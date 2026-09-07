import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import get_current_user
from ..db import get_db, now_iso

router = APIRouter(prefix="/api/prices", tags=["prices"])


def log_audit(conn, user_id: str, action: str, entity_type: str, entity_id: str = None, old_values: dict = None, new_values: dict = None):
    conn.execute(
        """
        INSERT INTO audit_log (user_id, action, entity_type, entity_id, old_values, new_values, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, action, entity_type, str(entity_id), json.dumps(old_values) if old_values else None, json.dumps(new_values) if new_values else None, now_iso()),
    )


def can_edit_price(user: dict) -> bool:
    # Админ всегда может редактировать
    if user["role"] == "admin":
        return True
    # Менеджер только с флагом
    if user["role"] == "manager" and user.get("can_edit_price"):
        return True
    return False


class PriceCategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    sort_order: int = Field(default=0)


class PriceItemIn(BaseModel):
    category_id: int
    name: str = Field(min_length=1, max_length=300)
    price: str = Field(default="0")  # Теперь строка для поддержки диапазонов
    unit: str = Field(default="шт")
    sort_order: int = Field(default=0)


UNITS = {"шт", "м", "м/пог", "м2"}


@router.get("")
def get_prices(user: dict = Depends(get_current_user)) -> list[dict]:
    conn = get_db()
    try:
        categories = conn.execute(
            "SELECT * FROM price_categories ORDER BY sort_order, name"
        ).fetchall()
        
        result = []
        for cat in categories:
            cat_dict = dict(cat)
            items = conn.execute(
                "SELECT * FROM price_items WHERE category_id = ? ORDER BY sort_order, name",
                (cat["id"],)
            ).fetchall()
            cat_dict["items"] = [dict(item) for item in items]
            result.append(cat_dict)
        
        return result
    finally:
        conn.close()


@router.post("/categories")
def create_category(payload: PriceCategoryIn, user: dict = Depends(get_current_user)) -> dict:
    if not can_edit_price(user):
        raise HTTPException(403, "Нет прав на редактирование прайса")
    
    conn = get_db()
    try:
        exists = conn.execute(
            "SELECT id FROM price_categories WHERE name = ?", (payload.name,)
        ).fetchone()
        if exists:
            raise HTTPException(400, "Категория с таким названием уже существует")
        
        cur = conn.execute(
            "INSERT INTO price_categories (name, sort_order) VALUES (?, ?)",
            (payload.name, payload.sort_order)
        )
        conn.commit()
        
        log_audit(conn, user["id"], "create", "price_category", cur.lastrowid, None, payload.model_dump())
        
        return {"ok": True, "id": cur.lastrowid}
    finally:
        conn.close()


@router.put("/categories/{cat_id}")
def update_category(cat_id: int, payload: PriceCategoryIn, user: dict = Depends(get_current_user)) -> dict:
    if not can_edit_price(user):
        raise HTTPException(403, "Нет прав на редактирование прайса")
    
    conn = get_db()
    try:
        old = conn.execute(
            "SELECT * FROM price_categories WHERE id = ?", (cat_id,)
        ).fetchone()
        if not old:
            raise HTTPException(404, "Категория не найдена")
        
        conn.execute(
            "UPDATE price_categories SET name = ?, sort_order = ? WHERE id = ?",
            (payload.name, payload.sort_order, cat_id)
        )
        conn.commit()
        
        log_audit(conn, user["id"], "update", "price_category", cat_id, dict(old), payload.model_dump())
        
        return {"ok": True}
    finally:
        conn.close()


@router.delete("/categories/{cat_id}")
def delete_category(cat_id: int, user: dict = Depends(get_current_user)) -> dict:
    if not can_edit_price(user):
        raise HTTPException(403, "Нет прав на редактирование прайса")
    
    conn = get_db()
    try:
        old = conn.execute(
            "SELECT * FROM price_categories WHERE id = ?", (cat_id,)
        ).fetchone()
        if not old:
            raise HTTPException(404, "Категория не найдена")
        
        conn.execute("DELETE FROM price_items WHERE category_id = ?", (cat_id,))
        conn.execute("DELETE FROM price_categories WHERE id = ?", (cat_id,))
        conn.commit()
        
        log_audit(conn, user["id"], "delete", "price_category", cat_id, dict(old), None)
        
        return {"ok": True}
    finally:
        conn.close()


@router.post("/items")
def create_item(payload: PriceItemIn, user: dict = Depends(get_current_user)) -> dict:
    if not can_edit_price(user):
        raise HTTPException(403, "Нет прав на редактирование прайса")
    
    if payload.unit not in UNITS:
        raise HTTPException(400, f"Некорректная единица измерения. Допустимые: {', '.join(UNITS)}")
    
    conn = get_db()
    try:
        cat = conn.execute(
            "SELECT id FROM price_categories WHERE id = ?", (payload.category_id,)
        ).fetchone()
        if not cat:
            raise HTTPException(400, "Категория не найдена")
        
        cur = conn.execute(
            """
            INSERT INTO price_items (category_id, name, price, unit, sort_order)
            VALUES (?, ?, ?, ?, ?)
            """,
            (payload.category_id, payload.name, payload.price, payload.unit, payload.sort_order)
        )
        conn.commit()
        
        log_audit(conn, user["id"], "create", "price_item", cur.lastrowid, None, payload.model_dump())
        
        return {"ok": True, "id": cur.lastrowid}
    finally:
        conn.close()


@router.put("/items/{item_id}")
def update_item(item_id: int, payload: PriceItemIn, user: dict = Depends(get_current_user)) -> dict:
    if not can_edit_price(user):
        raise HTTPException(403, "Нет прав на редактирование прайса")
    
    if payload.unit not in UNITS:
        raise HTTPException(400, f"Некорректная единица измерения. Допустимые: {', '.join(UNITS)}")
    
    conn = get_db()
    try:
        old = conn.execute(
            "SELECT * FROM price_items WHERE id = ?", (item_id,)
        ).fetchone()
        if not old:
            raise HTTPException(404, "Позиция не найдена")
        
        conn.execute(
            """
            UPDATE price_items SET category_id = ?, name = ?, price = ?, unit = ?, sort_order = ?
            WHERE id = ?
            """,
            (payload.category_id, payload.name, payload.price, payload.unit, payload.sort_order, item_id)
        )
        conn.commit()
        
        log_audit(conn, user["id"], "update", "price_item", item_id, dict(old), payload.model_dump())
        
        return {"ok": True}
    finally:
        conn.close()


@router.delete("/items/{item_id}")
def delete_item(item_id: int, user: dict = Depends(get_current_user)) -> dict:
    if not can_edit_price(user):
        raise HTTPException(403, "Нет прав на редактирование прайса")
    
    conn = get_db()
    try:
        old = conn.execute(
            "SELECT * FROM price_items WHERE id = ?", (item_id,)
        ).fetchone()
        if not old:
            raise HTTPException(404, "Позиция не найдена")
        
        conn.execute("DELETE FROM price_items WHERE id = ?", (item_id,))
        conn.commit()
        
        log_audit(conn, user["id"], "delete", "price_item", item_id, dict(old), None)
        
        return {"ok": True}
    finally:
        conn.close()


@router.get("/export")
def export_prices(user: dict = Depends(get_current_user)) -> dict:
    conn = get_db()
    try:
        categories = conn.execute(
            "SELECT * FROM price_categories ORDER BY sort_order, name"
        ).fetchall()
        
        csv_lines = ["Категория,Наименование,Цена,Ед.изм."]
        for cat in categories:
            items = conn.execute(
                "SELECT * FROM price_items WHERE category_id = ? ORDER BY sort_order, name",
                (cat["id"],)
            ).fetchall()
            for item in items:
                csv_lines.append(f'"{cat["name"]}","{item["name"]}",{item["price"]},"{item["unit"]}"')
        
        return {"csv": "\n".join(csv_lines)}
    finally:
        conn.close()