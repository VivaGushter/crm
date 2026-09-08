import hashlib
import secrets
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

from .db import get_db
from .sessions import get_session

security = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return secrets.compare_digest(hash_password(password), password_hash)


def get_current_user(token: Optional[str] = Depends(security)) -> Optional[dict]:
    """Получить текущего пользователя по Bearer токену."""
    if not token:
        return None
    session = get_session(token)
    if not session:
        return None
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id, name, role, theme, can_edit_price, can_edit_requests, can_delete_requests FROM users WHERE id = ?",
            (session["user_id"],)
        ).fetchone()
        return dict(user) if user else None
    finally:
        conn.close()


def require_auth(user: Optional[dict] = Depends(get_current_user)) -> dict:
    """Требовать авторизацию. Вызывать в роутах."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_admin(user: dict = Depends(require_auth)) -> dict:
    """Требовать роль администратора."""
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def require_manager_or_admin(user: dict = Depends(require_auth)) -> dict:
    """Требовать роль менеджера или администратора."""
    if user["role"] not in ("manager", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Manager or admin access required")
    return user
