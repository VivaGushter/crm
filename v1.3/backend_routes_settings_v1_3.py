import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import get_current_user
from ..db import get_db, now_iso

router = APIRouter(prefix="/api", tags=["settings", "analytics", "audit", "clients"])


class UserSettings(BaseModel):
    theme: str = Field(default="light", pattern="^(light|dark)$")


def log_audit(conn, user_id: str, action: str, entity_type: str, entity_id: str = None, old_values: dict = None, new_values: dict = None):
    conn.execute(
        """
        INSERT INTO audit_log (user_id, action, entity_type, entity_id, old_values, new_values, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, action, entity_type, str(entity_id), json.dumps(old_values) if old_values else None, json.dumps(new_values) if new_values else None, now_iso()),
    )


@router.get("/me")
def get_me_settings(user: dict = Depends(get_current_user)) -> dict:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, name, role, theme FROM users WHERE id = ?", (user["id"],)
        ).fetchone()
        if not row:
            raise HTTPException(404, "User not found")
        return dict(row)
    finally:
        conn.close()


@router.put("/me/settings")
def update_me_settings(payload: UserSettings, user: dict = Depends(get_current_user)) -> dict:
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET theme = ? WHERE id = ?", (payload.theme, user["id"])
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


@router.get("/analytics/summary")
def analytics_summary(user: dict = Depends(get_current_user)) -> dict:
    conn = get_db()
    try:
        # Фильтр для мастеров — только свои заявки
        if user["role"] == "user":
            base_where = "WHERE r.assignee = ?"
            base_params = [user["id"]]
        else:
            base_where = "WHERE 1=1"
            base_params = []

        # Общая статистика
        total = conn.execute(f"SELECT COUNT(*) AS count FROM requests r {base_where}", base_params).fetchone()["count"]
        completed = conn.execute(f"SELECT COUNT(*) AS count FROM requests r {base_where} AND r.status = 'done'", base_params).fetchone()["count"]
        active = conn.execute(f"SELECT COUNT(*) AS count FROM requests r {base_where} AND r.status IN ('new', 'scheduled', 'work')", base_params).fetchone()["count"]
        revenue = conn.execute(f"SELECT COALESCE(SUM(r.price), 0) AS sum FROM requests r {base_where} AND r.status = 'done'", base_params).fetchone()["sum"]

        # Статусы
        by_status = {}
        for row in conn.execute(f"SELECT r.status, COUNT(*) AS count, COALESCE(SUM(r.price), 0) AS revenue FROM requests r {base_where} GROUP BY r.status", base_params):
            by_status[row["status"]] = {"count": row["count"], "revenue": row["revenue"]}

        # Источники
        by_source = {}
        for row in conn.execute(f"SELECT r.source, COUNT(*) AS count, COALESCE(SUM(r.price), 0) AS revenue FROM requests r {base_where} GROUP BY r.source", base_params):
            by_source[row["source"]] = {"count": row["count"], "revenue": row["revenue"]}

        # Заявки по дням (последние 30 дней)
        daily = []
        for row in conn.execute(f"""
            SELECT substr(r.visit_date, 1, 10) AS day, COUNT(*) AS count
            FROM requests r {base_where}
            AND substr(r.visit_date, 1, 10) >= date('now', '-30 days')
            GROUP BY day
            ORDER BY day
            """, base_params):
            daily.append({"day": row["day"], "count": row["count"]})

        # Топ клиентов
        top_clients = []
        for row in conn.execute(f"""
            SELECT r.client, COUNT(*) AS count, COALESCE(SUM(r.price), 0) AS revenue
            FROM requests r {base_where}
            GROUP BY r.client
            ORDER BY count DESC
            LIMIT 10
            """, base_params):
            top_clients.append({
                "client": row["client"],
                "count": row["count"],
                "revenue": row["revenue"],
            })

        # Рейтинг мастеров (только для admin/manager)
        masters_ranking = []
        if user["role"] in ("admin", "manager"):
            for row in conn.execute("""
                SELECT u.name, u.id, COUNT(r.id) AS count, COALESCE(SUM(CASE WHEN r.status='done' THEN r.price ELSE 0 END), 0) AS revenue
                FROM users u
                LEFT JOIN requests r ON u.id = r.assignee
                GROUP BY u.id, u.name
                ORDER BY count DESC
                """):
                masters_ranking.append({
                    "name": row["name"],
                    "id": row["id"],
                    "count": row["count"],
                    "revenue": row["revenue"],
                })

        return {
            "total": total,
            "completed": completed,
            "active": active,
            "revenue": revenue,
            "by_status": by_status,
            "by_source": by_source,
            "daily": daily,
            "top_clients": top_clients,
            "masters_ranking": masters_ranking,
        }
    finally:
        conn.close()


@router.get("/audit")
def get_audit_log(user: dict = Depends(get_current_user)) -> list[dict]:
    if user["role"] not in ("admin", "manager"):
        raise HTTPException(403, "Доступ только для администраторов и менеджеров")
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT a.*, u.name AS user_name
            FROM audit_log a
            LEFT JOIN users u ON a.user_id = u.id
            ORDER BY a.created_at DESC
            LIMIT 100
            """
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@router.get("/clients")
def get_clients(user: dict = Depends(get_current_user)) -> list[dict]:
    conn = get_db()
    try:
        # Фильтр для мастеров
        if user["role"] == "user":
            sql = """
                SELECT r.client, COUNT(*) AS count, COALESCE(SUM(r.price), 0) AS revenue, MAX(r.visit_date) AS last_visit
                FROM requests r
                WHERE r.assignee = ?
                GROUP BY r.client
                ORDER BY last_visit DESC
            """
            params = [user["id"]]
        else:
            sql = """
                SELECT r.client, COUNT(*) AS count, COALESCE(SUM(r.price), 0) AS revenue, MAX(r.visit_date) AS last_visit
                FROM requests r
                GROUP BY r.client
                ORDER BY last_visit DESC
            """
            params = []
        
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@router.get("/clients/export")
def export_clients(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] not in ("admin", "manager"):
        raise HTTPException(403, "Доступ только для администраторов и менеджеров")
    conn = get_db()
    try:
        rows = conn.execute("""
            SELECT r.client, COUNT(*) AS count, COALESCE(SUM(r.price), 0) AS revenue, MAX(r.visit_date) AS last_visit
            FROM requests r
            GROUP BY r.client
            ORDER BY last_visit DESC
        """).fetchall()
        
        # Формируем CSV
        csv_lines = ["Клиент,Всего заявок,Выручка,Последняя заявка"]
        for row in rows:
            csv_lines.append(f'"{row["client"]}",{row["count"]},{row["revenue"]},"{row["last_visit"]}"')
        
        return {"csv": "\n".join(csv_lines)}
    finally:
        conn.close()


@router.get("/clients/{client_name}")
def get_client_detail(client_name: str, user: dict = Depends(get_current_user)) -> dict:
    conn = get_db()
    try:
        # Фильтр для мастеров
        if user["role"] == "user":
            sql = """
                SELECT r.*, COALESCE(u.name, r.assignee) AS assignee_name
                FROM requests r
                LEFT JOIN users u ON u.id = r.assignee
                WHERE r.client = ? AND r.assignee = ?
                ORDER BY r.visit_date DESC
            """
            params = [client_name, user["id"]]
        else:
            sql = """
                SELECT r.*, COALESCE(u.name, r.assignee) AS assignee_name
                FROM requests r
                LEFT JOIN users u ON u.id = r.assignee
                WHERE r.client = ?
                ORDER BY r.visit_date DESC
            """
            params = [client_name]
        
        rows = conn.execute(sql, params).fetchall()
        requests = [dict(row) for row in rows]
        
        if not rows:
            raise HTTPException(404, "Клиент не найден")
        
        total = len(requests)
        revenue = sum(r["price"] for r in requests if r["status"] == "done")
        
        return {
            "client": client_name,
            "total": total,
            "revenue": revenue,
            "requests": requests,
        }
    finally:
        conn.close()