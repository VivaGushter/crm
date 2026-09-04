from typing import Optional

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
        return {"ok": True, "id": cur.lastrowid}
    finally:
        conn.close()


@router.put("/{request_id}")
def update_request(request_id: int, payload: RequestIn, user: dict = Depends(get_current_user)) -> dict:
    conn = get_db()
    try:
        validate_request_payload(conn, payload, creating=False)
        exists = conn.execute("SELECT id FROM requests WHERE id = ?", (request_id,)).fetchone()
        if exists is None:
            raise HTTPException(404, "Заявка не найдена")
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
                now_iso(),
                request_id,
            ),
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.delete("/{request_id}")
def delete_request(request_id: int, user: dict = Depends(get_current_user)) -> dict:
    conn = get_db()
    try:
        cur = conn.execute("DELETE FROM requests WHERE id = ?", (request_id,))
        conn.commit()
        if not cur.rowcount:
            raise HTTPException(404, "Заявка не найдена")
        return {"ok": True}
    finally:
        conn.close()
