from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import get_current_user
from ..db import get_db

router = APIRouter(prefix="/api", tags=["settings", "analytics"])


class UserSettings(BaseModel):
    theme: str = Field(default="light", pattern="^(light|dark)$")


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
        # Общая статистика
        total = conn.execute("SELECT COUNT(*) AS count FROM requests").fetchone()["count"]
        completed = conn.execute(
            "SELECT COUNT(*) AS count FROM requests WHERE status = 'done'"
        ).fetchone()["count"]
        active = conn.execute(
            "SELECT COUNT(*) AS count FROM requests WHERE status IN ('new', 'scheduled', 'work')"
        ).fetchone()["count"]
        revenue = conn.execute(
            "SELECT COALESCE(SUM(price), 0) AS sum FROM requests WHERE status = 'done'"
        ).fetchone()["sum"]

        # Статусы
        by_status = {}
        for row in conn.execute(
            "SELECT status, COUNT(*) AS count, COALESCE(SUM(price), 0) AS revenue FROM requests GROUP BY status"
        ):
            by_status[row["status"]] = {"count": row["count"], "revenue": row["revenue"]}

        # Источники
        by_source = {}
        for row in conn.execute(
            "SELECT source, COUNT(*) AS count, COALESCE(SUM(price), 0) AS revenue FROM requests GROUP BY source"
        ):
            by_source[row["source"]] = {"count": row["count"], "revenue": row["revenue"]}

        # Заявки по дням (последние 30 дней)
        daily = []
        for row in conn.execute(
            """
            SELECT substr(visit_date, 1, 10) AS day, COUNT(*) AS count
            FROM requests
            WHERE substr(visit_date, 1, 10) >= date('now', '-30 days')
            GROUP BY day
            ORDER BY day
            """
        ):
            daily.append({"day": row["day"], "count": row["count"]})

        # Топ клиентов
        top_clients = []
        for row in conn.execute(
            """
            SELECT client, COUNT(*) AS count, COALESCE(SUM(price), 0) AS revenue
            FROM requests
            GROUP BY client
            ORDER BY count DESC
            LIMIT 10
            """
        ):
            top_clients.append({
                "client": row["client"],
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
        }
    finally:
        conn.close()