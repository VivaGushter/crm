from typing import Optional
import json

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import get_current_user
from ..config import CONTACT_METHODS, SOURCES, STATUSES
from ..db import get_db, now_iso
from ..schemas import RequestIn

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
    user: dict = Depends(get_current_user),
) -> list[dict]:
    sql = """
        SELECT r.*, COALESCE(u.name, r.assignee) AS assignee_name
        FROM requests r
        LEFT JOIN users u ON u.id = r.assignee
        WHERE 1 = 1
    """
    values = []
    
    # Мастер видит только свои заявки
    if user["role"] == "user":
        sql += " AND r.assignee = ?"
        values.append(user["id"])
    
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


@router.post("")
def create_request(payload: RequestIn, user: dict = Depends(get_current_user)) -> dict:
    # Мастер, менеджер и админ могут создавать
    if user["role"] not in ("user", "manager", "admin"):
        raise HTTPException(403, "Недостаточно прав")
    
    conn = get_db()
    try:
        validate_request_payload(conn, payload, creating=True)
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
                user["id"],
                now,
                payload.source,
                payload.contact_method,
            ),
        )
        conn.commit()
        
        # Аудит-лог
        log_audit(conn, user["id"], "create", "request", cur.lastrowid, None, payload.model_dump())
        
        return {"ok": True, "id": cur.lastrowid}
    finally:
        conn.close()


@router.put("/{request_id}")
def update_request(request_id: int, payload: RequestIn, user: dict = Depends(get_current_user)) -> dict:
    # Мастер, менеджер и админ могут редактировать
    if user["role"] not in ("user", "manager", "admin"):
        raise HTTPException(403, "Недостаточно прав")
    
    conn = get_db()
    try:
        validate_request_payload(conn, payload, creating=False)
        exists = conn.execute("SELECT id FROM requests WHERE id = ?", (request_id,)).fetchone()
        if exists is None:
            raise HTTPException(404, "Заявка не найдена")
        
        # Мастер может редактировать только свои заявки
        if user["role"] == "user":
            req = conn.execute("SELECT assignee FROM requests WHERE id = ?", (request_id,)).fetchone()
            if req["assignee"] != user["id"]:
                raise HTTPException(403, "Можно редактировать только свои заявки")
        
        # Получаем старые значения для аудита
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
        conn.commit()
        
        # Аудит-лог
        log_audit(conn, user["id"], "update", "request", request_id, old_values, payload.model_dump())
        
        return {"ok": True}
    finally:
        conn.close()


@router.delete("/{request_id}")
def delete_request(request_id: int, user: dict = Depends(get_current_user)) -> dict:
    # Только админ и менеджер могут удалять
    if user["role"] not in ("admin", "manager"):
        raise HTTPException(403, "Только администратор и менеджер могут удалять заявки")
    
    conn = get_db()
    try:
        # Получаем старые значения для аудита
        old = conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
        old_values = dict(old) if old else None
        
        cur = conn.execute("DELETE FROM requests WHERE id = ?", (request_id,))
        conn.commit()
        if not cur.rowcount:
            raise HTTPException(404, "Заявка не найдена")
        
        # Аудит-лог
        log_audit(conn, user["id"], "delete", "request", request_id, old_values, None)
        
        return {"ok": True}
    finally:
        conn.close()