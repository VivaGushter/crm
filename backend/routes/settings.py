from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import require_auth
from ..db import get_db

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsUpdate(BaseModel):
    theme: str = "light"


@router.get("")
def get_settings(current_user: dict = Depends(require_auth)) -> dict:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT theme FROM users WHERE id = ?",
            (current_user["id"],)
        ).fetchone()
        return {"theme": row["theme"]} if row else {"theme": "light"}
    finally:
        conn.close()


@router.put("")
def update_settings(payload: SettingsUpdate, current_user: dict = Depends(require_auth)) -> dict:
    if payload.theme not in ("light", "dark"):
        raise HTTPException(400, "Некорректная тема")
    conn = get_db()
    try:
        conn.execute(
            "UPDATE users SET theme = ? WHERE id = ?",
            (payload.theme, current_user["id"])
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()
