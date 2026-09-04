import json
from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_current_user, hash_password, require_admin
from ..db import get_db, now_iso
from ..schemas import UserCreate, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


def log_audit(conn, user_id: str, action: str, entity_type: str, entity_id: str = None, old_values: dict = None, new_values: dict = None):
    conn.execute(
        """
        INSERT INTO audit_log (user_id, action, entity_type, entity_id, old_values, new_values, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, action, entity_type, str(entity_id), json.dumps(old_values) if old_values else None, json.dumps(new_values) if new_values else None, now_iso()),
    )


@router.get("")
def list_users(user: dict = Depends(get_current_user)) -> list[dict]:
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, name, role, created_at FROM users ORDER BY name COLLATE NOCASE"
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@router.post("")
def create_user(payload: UserCreate, admin: dict = Depends(require_admin)) -> dict:
    if payload.role not in {"user", "manager", "admin"}:
        raise HTTPException(400, "Invalid role")
    conn = get_db()
    try:
        exists = conn.execute("SELECT id FROM users WHERE id = ?", (payload.id,)).fetchone()
        if exists:
            raise HTTPException(400, "Пользователь с таким логином уже существует")
        conn.execute(
            "INSERT INTO users (id, password_hash, name, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (payload.id, hash_password(payload.password), payload.name, payload.role, now_iso()),
        )
        conn.commit()
        
        # Аудит-лог
        log_audit(conn, admin["id"], "create", "user", payload.id, None, {"id": payload.id, "name": payload.name, "role": payload.role})
        
        return {"ok": True}
    finally:
        conn.close()


@router.put("/{user_id}")
def update_user(user_id: str, payload: UserUpdate, admin: dict = Depends(require_admin)) -> dict:
    if payload.role is not None and payload.role not in {"user", "manager", "admin"}:
        raise HTTPException(400, "Invalid role")
    conn = get_db()
    try:
        existing = conn.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if existing is None:
            raise HTTPException(404, "User not found")
        if user_id == admin["id"] and payload.role == "user":
            raise HTTPException(400, "Нельзя снять роль админа с текущего аккаунта")

        changes, values = [], []
        old_values = dict(existing)
        
        if payload.name is not None:
            changes.append("name = ?")
            values.append(payload.name)
        if payload.password:
            changes.append("password_hash = ?")
            values.append(hash_password(payload.password))
        if payload.role is not None:
            changes.append("role = ?")
            values.append(payload.role)
        if changes:
            values.append(user_id)
            conn.execute(f"UPDATE users SET {', '.join(changes)} WHERE id = ?", values)
            conn.commit()
            
            # Аудит-лог
            new_values = {**old_values, **{k: v for k, v in zip(["name", "password_hash", "role"], values) if v}}
            log_audit(conn, admin["id"], "update", "user", user_id, old_values, new_values)
            
        return {"ok": True}
    finally:
        conn.close()


@router.delete("/{user_id}")
def delete_user(user_id: str, admin: dict = Depends(require_admin)) -> dict:
    if user_id == admin["id"]:
        raise HTTPException(400, "Нельзя удалить свой текущий аккаунт")
    conn = get_db()
    try:
        user_row = conn.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if user_row is None:
            raise HTTPException(404, "User not found")
        if user_row["role"] == "admin":
            admins = conn.execute(
                "SELECT COUNT(*) AS count FROM users WHERE role = 'admin'"
            ).fetchone()["count"]
            if admins <= 1:
                raise HTTPException(400, "Нельзя удалить последнего администратора")
        references = conn.execute(
            "SELECT COUNT(*) AS count FROM requests WHERE assignee = ?", (user_id,)
        ).fetchone()["count"]
        if references:
            raise HTTPException(400, "Нельзя удалить пользователя: на него назначены заявки")
        
        # Аудит-лог
        log_audit(conn, admin["id"], "delete", "user", user_id, dict(user_row), None)
        
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()