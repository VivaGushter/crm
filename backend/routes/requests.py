from typing import Optional
import json

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import require_auth
from ..config import CONTACT_METHODS, SOURCES, STATUSES
from ..db import get_db, now_iso
from ..schemas import RequestIn, RequestItemIn

router = APIRouter(prefix="/api/requests", tags=["requests"])


def validate_request_payload(conn, payload: RequestIn, creating: bool = False) -> None:
    if payload.status not in STATUSES:
        raise HTTPException(400, "Некорректный статус")
    if payload.source not in SOURCES:
        raise HTTPException(400, "Некорректный канал обращения")
    if payload.contact_method not in CONTACT_METHODS:
        raise HTTPException(400, "Некорректный способ связи")
    if creating and payload.source == "unknown":
        raise HTTPException(400, "Для новой заявки выберите канал обращения")
    assignee = conn.execute("SELECT id FROM users WHERE id = ?", (payload.assignee,)).fetchone()
    if assignee is None:
        raise HTTPException(400, "Выбранный исполнитель не существует")


def validate_items_total(payload: RequestIn) -> None:
    if not payload.items:
        return
    calculated = round(sum(i.unit_price * i.quantity for i in payload.items), 2)
    if abs(calculated - payload.price) > 1:
        raise HTTPException(400, "Сумма заявки не совпадает с суммой позиций калькуляции")


def save_request_items(conn, request_id: int, items: list[RequestItemIn]) -> None:
    """Полностью перезаписывает состав работ заявки (удалить всё → вставить заново)."""
    conn.execute("DELETE FROM request_calculation_items WHERE request_id = ?", (request_id,))
    now = now_iso()
    for idx, item in enumerate(items):
        line_total = round(item.unit_price * item.quantity, 2)
        conn.execute(
            """
            INSERT INTO request_calculation_items
            (request_id, price_item_id, category_name_snapshot, name_snapshot,
             unit_snapshot, unit_price, quantity, line_total, sort_order, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                item.price_item_id,
                item.category_name,
                item.name,
                item.unit,
                item.unit_price,
                item.quantity,
                line_total,
                idx,
                now,
            ),
        )


def fetch_request_items(conn, request_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM request_calculation_items WHERE request_id = ? ORDER BY sort_order, id",
        (request_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def log_audit(conn, user_id: str, action: str, entity_type: str, entity_id: str = None, old_values: dict = None, new_values: dict = None):
    conn.execute(
        """
        INSERT INTO audit_log (user_id, action, entity_type, entity_id, old_values, new_values, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, action, entity_type, str(entity_id), json.dumps(old_values) if old_values else None, json.dumps(new_values) if new_values else None, now_iso()),
    )


@router.get("")
def list_requests(
    search: str = "",
    status: str = "all",
    assignee: str = "all",
    source: str = "all",
    contact_method: str = "all",
    date_from: Optional[str] = Query(default=None),
    date_to: Optional[str] = Query(default=None),
    current_user: dict = Depends(require_auth),
) -> list[dict]:
    sql = """
        SELECT r.*, COALESCE(u.name, r.assignee) AS assignee_name
        FROM requests r
        LEFT JOIN users u ON u.id = r.assignee
        WHERE 1 = 1
    """
    values = []

    # Мастер видит только свои заявки
    if current_user["role"] == "user":
        sql += " AND r.assignee = ?"
        values.append(current_user["id"])

    if search.strip():
        like = f"%{search.strip()}%"
        sql += """ AND (
            r.client LIKE ? COLLATE NOCASE OR
            r.address LIKE ? COLLATE NOCASE OR
            r.phone LIKE ? COLLATE NOCASE OR
            COALESCE(r.comment, '') LIKE ? COLLATE NOCASE
        ) """
        values.extend([like, like, like, like])
    if status != "all":
        if status not in STATUSES:
            raise HTTPException(400, "Некорректный статус")
        sql += " AND r.status = ?"
        values.append(status)
    if assignee != "all":
        sql += " AND r.assignee = ?"
        values.append(assignee)
    if source != "all":
        if source not in SOURCES:
            raise HTTPException(400, "Некорректный канал обращения")
        sql += " AND r.source = ?"
        values.append(source)
    if contact_method != "all":
        if contact_method not in CONTACT_METHODS:
            raise HTTPException(400, "Некорректный способ связи")
        sql += " AND r.contact_method = ?"
        values.append(contact_method)
    if date_from:
        sql += " AND substr(r.visit_date, 1, 10) >= ?"
        values.append(date_from)
    if date_to:
        sql += " AND substr(r.visit_date, 1, 10) <= ?"
        values.append(date_to)
    sql += " ORDER BY r.visit_date ASC, r.id DESC"

    conn = get_db()
    try:
        rows = conn.execute(sql, values).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@router.get("/{request_id}")
def get_request(request_id: int, current_user: dict = Depends(require_auth)) -> dict:
    conn = get_db()
    try:
        row = conn.execute(
            """
            SELECT r.*, COALESCE(u.name, r.assignee) AS assignee_name
            FROM requests r
            LEFT JOIN users u ON u.id = r.assignee
            WHERE r.id = ?
            """,
            (request_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(404, "Заявка не найдена")
        if current_user["role"] == "user" and row["assignee"] != current_user["id"]:
            raise HTTPException(403, "Недостаточно прав")
        data = dict(row)
        data["items"] = fetch_request_items(conn, request_id)
        return data
    finally:
        conn.close()


@router.post("")
def create_request(payload: RequestIn, current_user: dict = Depends(require_auth)) -> dict:
    if current_user["role"] not in ("user", "manager", "admin"):
        raise HTTPException(403, "Недостаточно прав")

    conn = get_db()
    try:
        validate_request_payload(conn, payload, creating=True)
        validate_items_total(payload)
        now = now_iso()
        cur = conn.execute(
            """
            INSERT INTO requests
            (client, visit_date, address, phone, status, price, comment, assignee, created_by, updated_at, source, contact_method)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.client,
                payload.visit_date,
                payload.address,
                payload.phone,
                payload.status,
                payload.price,
                payload.comment or "",
                payload.assignee,
                current_user["id"],
                now,
                payload.source,
                payload.contact_method,
            ),
        )
        request_id = cur.lastrowid
        if payload.items:
            save_request_items(conn, request_id, payload.items)
        conn.commit()
        log_audit(conn, current_user["id"], "create", "request", request_id, None, payload.model_dump())
        return {"ok": True, "id": request_id}
    finally:
        conn.close()


@router.put("/{request_id}")
def update_request(request_id: int, payload: RequestIn, current_user: dict = Depends(require_auth)) -> dict:
    if current_user["role"] not in ("user", "manager", "admin"):
        raise HTTPException(403, "Недостаточно прав")

    conn = get_db()
    try:
        validate_request_payload(conn, payload, creating=False)
        validate_items_total(payload)
        exists = conn.execute("SELECT id FROM requests WHERE id = ?", (request_id,)).fetchone()
        if exists is None:
            raise HTTPException(404, "Заявка не найдена")
        if current_user["role"] == "user":
            req = conn.execute("SELECT assignee FROM requests WHERE id = ?", (request_id,)).fetchone()
            if req["assignee"] != current_user["id"]:
                raise HTTPException(403, "Можно редактировать только свои заявки")
        old = conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
        old_values = dict(old) if old else None
        now = now_iso()
        conn.execute(
            """
            UPDATE requests SET
                client=?, visit_date=?, address=?, phone=?, status=?, price=?, comment=?,
                assignee=?, source=?, contact_method=?, updated_at=?
            WHERE id=?
            """,
            (
                payload.client,
                payload.visit_date,
                payload.address,
                payload.phone,
                payload.status,
                payload.price,
                payload.comment or "",
                payload.assignee,
                payload.source,
                payload.contact_method,
                now,
                request_id,
            ),
        )
        # Состав пересохраняется, только если поле items явно передано.
        # None означает "состав не трогать", пустой список [] означает "очистить состав".
        if payload.items is not None:
            save_request_items(conn, request_id, payload.items)
        conn.commit()
        log_audit(conn, current_user["id"], "update", "request", request_id, old_values, payload.model_dump())
        return {"ok": True}
    finally:
        conn.close()


@router.delete("/{request_id}")
def delete_request(request_id: int, current_user: dict = Depends(require_auth)) -> dict:
    if current_user["role"] not in ("admin", "manager"):
        raise HTTPException(403, "Только администратор и менеджер могут удалять заявки")

    conn = get_db()
    try:
        old = conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
        old_values = dict(old) if old else None
        cur = conn.execute("DELETE FROM requests WHERE id = ?", (request_id,))
        conn.commit()
        if not cur.rowcount:
            raise HTTPException(404, "Заявка не найдена")
        log_audit(conn, current_user["id"], "delete", "request", request_id, old_values, None)
        return {"ok": True}
    finally:
        conn.close()
