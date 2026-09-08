from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..auth import require_admin, require_auth, require_manager_or_admin
from ..db import get_db

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AnalyticsSummary(BaseModel):
    total: int
    active: int
    completed: int
    revenue: float


@router.get("/analytics/summary")
def analytics_summary(current_user: dict = Depends(require_auth)) -> dict:
    conn = get_db()
    try:
        total = conn.execute("SELECT COUNT(*) AS c FROM requests").fetchone()["c"]
        active = conn.execute("SELECT COUNT(*) AS c FROM requests WHERE status IN ('new', 'scheduled', 'work')").fetchone()["c"]
        completed = conn.execute("SELECT COUNT(*) AS c FROM requests WHERE status = 'done'").fetchone()["c"]
        revenue = conn.execute("SELECT COALESCE(SUM(price), 0) AS s FROM requests WHERE status = 'done'").fetchone()["s"]
        
        by_status = {}
        for status in ["new", "scheduled", "work", "done", "cancel"]:
            rows = conn.execute(
                "SELECT status, COALESCE(SUM(price), 0) AS revenue, COUNT(*) AS count FROM requests WHERE status = ? GROUP BY status",
                (status,)
            ).fetchall()
            row = rows[0] if rows else {"status": status, "revenue": 0, "count": 0}
            by_status[status] = {"count": row["count"], "revenue": float(row["revenue"])}
        
        by_source = {}
        for src in ["unknown", "avito", "house_chats"]:
            rows = conn.execute(
                "SELECT source, COALESCE(SUM(price), 0) AS revenue, COUNT(*) AS count FROM requests WHERE (source IS NULL OR source = ?) AND status = 'done' GROUP BY source",
                (src,)
            ).fetchall()
            row = rows[0] if rows else {"source": src, "revenue": 0, "count": 0}
            by_source[src] = {"count": row["count"], "revenue": float(row["revenue"])}
        
        masters = conn.execute(
            """
            SELECT u.name, COALESCE(SUM(r.price), 0) AS revenue, COUNT(r.id) AS count
            FROM users u
            LEFT JOIN requests r ON r.assignee = u.id AND r.status = 'done'
            WHERE u.role = 'user'
            GROUP BY u.id, u.name
            ORDER BY count DESC
            LIMIT 5
            """
        ).fetchall()
        masters_ranking = [{"name": m["name"], "count": m["count"], "revenue": float(m["revenue"])} for m in masters]
        
        clients = conn.execute(
            """
            SELECT client, COALESCE(SUM(price), 0) AS revenue, COUNT(*) AS count, MAX(visit_date) AS last_visit
            FROM requests
            WHERE status = 'done'
            GROUP BY client
            ORDER BY count DESC
            LIMIT 5
            """
        ).fetchall()
        top_clients = [{"client": c["client"], "count": c["count"], "revenue": float(c["revenue"])} for c in clients]
        
        return {
            "total": total,
            "active": active,
            "completed": completed,
            "revenue": float(revenue),
            "by_status": by_status,
            "by_source": by_source,
            "masters_ranking": masters_ranking,
            "top_clients": top_clients,
        }
    finally:
        conn.close()


@router.get("/clients")
def list_clients(current_user: dict = Depends(require_auth)) -> list[dict]:
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT client, COALESCE(SUM(price), 0) AS revenue, COUNT(*) AS count, MAX(visit_date) AS last_visit
            FROM requests
            WHERE status = 'done'
            GROUP BY client
            ORDER BY last_visit DESC
            LIMIT 50
            """
        ).fetchall()
        return [
            {
                "client": r["client"],
                "count": r["count"],
                "revenue": float(r["revenue"]),
                "last_visit": r["last_visit"],
            }
            for r in rows
        ]
    finally:
        conn.close()


@router.get("/clients/export")
def export_clients(current_user: dict = Depends(require_auth)) -> dict:
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT client, phone, address, COALESCE(SUM(price), 0) AS revenue, COUNT(*) AS count, MAX(visit_date) AS last_visit
            FROM requests
            WHERE status = 'done'
            GROUP BY client, phone, address
            ORDER BY last_visit DESC
            """
        ).fetchall()
        csv_lines = ["client,phone,address,revenue,count,last_visit"]
        for r in rows:
            csv_lines.append(f'"{r["client"]}","{r["phone"]}","{r["address"]}",{r["revenue"]},{r["count"]},"{r["last_visit"]}"')
        return {"csv": "\n".join(csv_lines)}
    finally:
        conn.close()


@router.get("/clients/{client_name}")
def get_client(client_name: str, current_user: dict = Depends(require_auth)) -> dict:
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT * FROM requests
            WHERE client = ?
            ORDER BY visit_date DESC
            """,
            (client_name,),
        ).fetchall()
        if not rows:
            from fastapi import HTTPException
            raise HTTPException(404, "Клиент не найден")
        total = len(rows)
        revenue = sum(float(r["price"] or 0) for r in rows)
        return {
            "client": client_name,
            "total": total,
            "revenue": revenue,
            "requests": [dict(r) for r in rows],
        }
    finally:
        conn.close()


@router.get("/audit")
def get_audit(current_user: dict = Depends(require_manager_or_admin)) -> list[dict]:
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT a.*, u.name AS user_name
            FROM audit_log a
            LEFT JOIN users u ON u.id = a.user_id
            ORDER BY a.created_at DESC
            LIMIT 100
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
