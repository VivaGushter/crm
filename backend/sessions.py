import secrets
from datetime import datetime, timedelta
from typing import Optional

from .db import get_db, now_iso


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def create_session(user_id: str) -> str:
    """Создать новую сессию, вернуть токен."""
    token = generate_token()
    expires = datetime.now() + timedelta(days=30)
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, now_iso(), expires.isoformat(timespec='minutes'))
        )
        conn.commit()
        return token
    finally:
        conn.close()


def get_session(token: str) -> Optional[dict]:
    """Получить сессию по токену. Если истекла — удалить и вернуть None."""
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT token, user_id, created_at, expires_at FROM sessions WHERE token = ?",
            (token,)
        ).fetchone()
        if not row:
            return None
        if datetime.fromisoformat(row["expires_at"]) < datetime.now():
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            return None
        return dict(row)
    finally:
        conn.close()


def delete_session(token: str) -> bool:
    """Удалить сессию (logout)."""
    conn = get_db()
    try:
        cur = conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def delete_all_user_sessions(user_id: str) -> int:
    """Удалить все сессии пользователя (смена пароля, отзыв доступа)."""
    conn = get_db()
    try:
        cur = conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def cleanup_expired_sessions() -> int:
    """Удалить все истёкшие сессии. Вызывать периодически."""
    conn = get_db()
    try:
        now = datetime.now().isoformat(timespec='minutes')
        cur = conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()
