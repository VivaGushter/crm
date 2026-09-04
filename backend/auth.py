import hashlib
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .db import get_db

security = HTTPBasic()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_current_user(credentials: HTTPBasicCredentials = Depends(security)) -> dict:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT id, password_hash, name, role FROM users WHERE id = ?",
            (credentials.username,),
        ).fetchone()
    finally:
        conn.close()

    if row is None or not secrets.compare_digest(
        row["password_hash"], hash_password(credentials.password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return {"id": row["id"], "name": row["name"], "role": row["role"]}


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user
