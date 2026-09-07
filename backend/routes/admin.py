import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from ..auth import get_current_user, hash_password
from ..db import get_db, now_iso

router = APIRouter(prefix="/api/admin", tags=["admin"])


def log_audit(conn, user_id: str, action: str, entity_type: str, entity_id: str = None, old_values: dict = None, new_values: dict = None):
    conn.execute(
        """
        INSERT INTO audit_log (user_id, action, entity_type, entity_id, old_values, new_values, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, action, entity_type, str(entity_id), json.dumps(old_values) if old_values else None, json.dumps(new_values) if new_values else None, now_iso()),
    )


class UserPermissions(BaseModel):
    can_edit_price: Optional[bool] = None
    can_edit_requests: Optional[bool] = None
    can_delete_requests: Optional[bool] = None


@router.get("/users")
def get_all_users(user: dict = Depends(get_current_user)) -> list[dict]:
    if user["role"] != "admin":
        raise HTTPException(403, "Только администратор может управлять пользователями")
    
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT id, name, role, created_at, can_edit_price, can_edit_requests, can_delete_requests
            FROM users
            ORDER BY name COLLATE NOCASE
            """
        ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            # Админ всегда имеет все права
            if d["role"] == "admin":
                d["can_edit_price"] = 1
                d["can_edit_requests"] = 1
                d["can_delete_requests"] = 1
            result.append(d)
        return result
    finally:
        conn.close()


@router.put("/users/{user_id}/permissions")
def update_user_permissions(user_id: str, payload: UserPermissions, user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "Только администратор может управлять правами")
    
    conn = get_db()
    try:
        target = conn.execute(
            "SELECT id, role, can_edit_price, can_edit_requests, can_delete_requests FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        if not target:
            raise HTTPException(404, "Пользователь не найден")
        
        if target["role"] not in ("manager",):
            raise HTTPException(400, "Права можно назначать только менеджерам")
        
        old_values = {
            "can_edit_price": bool(target["can_edit_price"]),
            "can_edit_requests": bool(target["can_edit_requests"]),
            "can_delete_requests": bool(target["can_delete_requests"]),
        }
        
        changes = []
        values = []
        
        if payload.can_edit_price is not None:
            changes.append("can_edit_price = ?")
            values.append(1 if payload.can_edit_price else 0)
        if payload.can_edit_requests is not None:
            changes.append("can_edit_requests = ?")
            values.append(1 if payload.can_edit_requests else 0)
        if payload.can_delete_requests is not None:
            changes.append("can_delete_requests = ?")
            values.append(1 if payload.can_delete_requests else 0)
        
        if changes:
            values.append(user_id)
            conn.execute(f"UPDATE users SET {', '.join(changes)} WHERE id = ?", values)
            conn.commit()
            
            new_values = {
                "can_edit_price": bool(payload.can_edit_price) if payload.can_edit_price is not None else old_values["can_edit_price"],
                "can_edit_requests": bool(payload.can_edit_requests) if payload.can_edit_requests is not None else old_values["can_edit_requests"],
                "can_delete_requests": bool(payload.can_delete_requests) if payload.can_delete_requests is not None else old_values["can_delete_requests"],
            }
            
            log_audit(conn, user["id"], "update_permissions", "user", user_id, old_values, new_values)
        
        return {"ok": True}
    finally:
        conn.close()


@router.post("/users")
def create_user(payload: dict, user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "Только администратор может создавать пользователей")
    
    required = ["id", "name", "password", "role"]
    for field in required:
        if field not in payload or not payload[field]:
            raise HTTPException(400, f"Поле '{field}' обязательно")
    
    if payload["role"] not in ("user", "manager", "admin"):
        raise HTTPException(400, "Некорректная роль")
    
    conn = get_db()
    try:
        exists = conn.execute("SELECT id FROM users WHERE id = ?", (payload["id"],)).fetchone()
        if exists:
            raise HTTPException(400, "Пользователь с таким логином уже существует")
        
        # Админ по умолчанию имеет все права, остальные - только can_edit_requests
        if payload["role"] == "admin":
            perms = (1, 1, 1)
        else:
            perms = (0, 1, 0)
        
        conn.execute(
            """
            INSERT INTO users (id, password_hash, name, role, created_at, can_edit_price, can_edit_requests, can_delete_requests)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (payload["id"], hash_password(payload["password"]), payload["name"], payload["role"], now_iso(), *perms)
        )
        conn.commit()
        
        log_audit(conn, user["id"], "create", "user", payload["id"], None, payload)
        
        return {"ok": True}
    finally:
        conn.close()


@router.put("/users/{user_id}")
def update_user(user_id: str, payload: dict, user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "Только администратор может редактировать пользователей")
    
    conn = get_db()
    try:
        existing = conn.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Пользователь не найден")
        
        changes = []
        values = []
        old_values = dict(existing)
        
        if "name" in payload and payload["name"]:
            changes.append("name = ?")
            values.append(payload["name"])
        if "password" in payload and payload["password"]:
            changes.append("password_hash = ?")
            values.append(hash_password(payload["password"]))
        if "role" in payload and payload["role"]:
            if payload["role"] not in ("user", "manager", "admin"):
                raise HTTPException(400, "Некорректная роль")
            changes.append("role = ?")
            values.append(payload["role"])
        
        if changes:
            values.append(user_id)
            conn.execute(f"UPDATE users SET {', '.join(changes)} WHERE id = ?", values)
            conn.commit()
            
            new_values = {**old_values, **{k: v for k, v in zip(["name", "role"], values[:2])}}
            log_audit(conn, user["id"], "update", "user", user_id, old_values, new_values)
        
        return {"ok": True}
    finally:
        conn.close()


@router.delete("/users/{user_id}")
def delete_user(user_id: str, user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "Только администратор может удалять пользователей")
    
    if user_id == user["id"]:
        raise HTTPException(400, "Нельзя удалить свой аккаунт")
    
    conn = get_db()
    try:
        target = conn.execute("SELECT id, role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not target:
            raise HTTPException(404, "Пользователь не найден")
        
        if target["role"] == "admin":
            admins = conn.execute("SELECT COUNT(*) AS count FROM users WHERE role = 'admin'").fetchone()["count"]
            if admins <= 1:
                raise HTTPException(400, "Нельзя удалить последнего администратора")
        
        references = conn.execute("SELECT COUNT(*) AS count FROM requests WHERE assignee = ?", (user_id,)).fetchone()["count"]
        if references:
            raise HTTPException(400, "Нельзя удалить пользователя: на него назначены заявки")
        
        log_audit(conn, user["id"], "delete", "user", user_id, dict(target), None)
        
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        
        return {"ok": True}
    finally:
        conn.close()