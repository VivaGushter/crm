from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import get_current_user
from ..config import ACTIVE_STATUSES, SOURCES
from ..db import get_db

router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("")
def report(
    date_from: str = Query(min_length=10, max_length=10),
    date_to: str = Query(min_length=10, max_length=10),
    user: dict = Depends(get_current_user),
) -> dict:
    if date_from > date_to:
        raise HTTPException(400, "Дата начала не может быть позже даты окончания")

    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT source, status, COALESCE(price, 0) AS price
            FROM requests
            WHERE substr(visit_date, 1, 10) >= ?
              AND substr(visit_date, 1, 10) <= ?
            """,
            (date_from, date_to),
        ).fetchall()
    finally:
        conn.close()

    total = len(rows)
    completed = sum(row["status"] == "done" for row in rows)
    cancelled = sum(row["status"] == "cancel" for row in rows)
    active = sum(row["status"] in ACTIVE_STATUSES for row in rows)
    revenue = sum(float(row["price"] or 0) for row in rows if row["status"] == "done")

    by_source = {}
    for key, label in SOURCES.items():
        source_rows = [row for row in rows if (row["source"] or "unknown") == key]
        by_source[key] = {
            "label": label,
            "total": len(source_rows),
            "completed": sum(row["status"] == "done" for row in source_rows),
            "revenue": sum(float(row["price"] or 0) for row in source_rows if row["status"] == "done"),
        }

    return {
        "date_from": date_from,
        "date_to": date_to,
        "total": total,
        "completed": completed,
        "cancelled": cancelled,
        "active": active,
        "revenue": revenue,
        "by_source": by_source,
    }
