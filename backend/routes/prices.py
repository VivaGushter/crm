from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import require_auth
from ..db import get_db, now_iso

router = APIRouter(prefix="/api/prices", tags=["prices"])


class CategoryIn(BaseModel):
    name: str
    sort_order: int = 0


class ItemIn(BaseModel):
    category_id: int
    name: str
    price: str = "0"
    unit: str = "шт"
    sort_order: int = 0


@router.get("")
def list_prices(current_user: dict = Depends(require_auth)) -> list[dict]:
    """Вернуть категории с вложенными позициями (для price.html)."""
    conn = get_db()
    try:
        cats = conn.execute("SELECT * FROM price_categories ORDER BY sort_order, name").fetchall()
        result = []
        for cat in cats:
            items = conn.execute(
                "SELECT * FROM price_items WHERE category_id = ? ORDER BY sort_order, name",
                (cat["id"],)
            ).fetchall()
            result.append({
                "id": cat["id"],
                "name": cat["name"],
                "sort_order": cat["sort_order"],
                "items": [dict(i) for i in items]
            })
        return result
    finally:
        conn.close()


@router.get("/categories")
def list_categories(current_user: dict = Depends(require_auth)) -> list[dict]:
    conn = get_db()
    try:
        rows = conn.execute("SELECT * FROM price_categories ORDER BY sort_order, name").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


@router.post("/categories")
def create_category(payload: CategoryIn, current_user: dict = Depends(require_auth)) -> dict:
    if current_user["role"] not in ("admin", "manager"):
        raise HTTPException(403, "Только администратор и менеджер могут управлять прайсом")
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO price_categories (name, sort_order) VALUES (?, ?)",
            (payload.name, payload.sort_order)
        )
        conn.commit()
        return {"ok": True, "id": cur.lastrowid}
    finally:
        conn.close()


@router.put("/categories/{cat_id}")
def update_category(cat_id: int, payload: CategoryIn, current_user: dict = Depends(require_auth)) -> dict:
    if current_user["role"] not in ("admin", "manager"):
        raise HTTPException(403, "Только администратор и менеджер могут управлять прайсом")
    conn = get_db()
    try:
        cur = conn.execute(
            "UPDATE price_categories SET name = ?, sort_order = ? WHERE id = ?",
            (payload.name, payload.sort_order, cat_id)
        )
        conn.commit()
        if not cur.rowcount:
            raise HTTPException(404, "Категория не найдена")
        return {"ok": True}
    finally:
        conn.close()


@router.delete("/categories/{cat_id}")
def delete_category(cat_id: int, current_user: dict = Depends(require_auth)) -> dict:
    if current_user["role"] not in ("admin", "manager"):
        raise HTTPException(403, "Только администратор и менеджер могут управлять прайсом")
    conn = get_db()
    try:
        cur = conn.execute("DELETE FROM price_categories WHERE id = ?", (cat_id,))
        conn.commit()
        if not cur.rowcount:
            raise HTTPException(404, "Категория не найдена")
        return {"ok": True}
    finally:
        conn.close()


@router.post("/items")
def create_item(payload: ItemIn, current_user: dict = Depends(require_auth)) -> dict:
    if current_user["role"] not in ("admin", "manager"):
        raise HTTPException(403, "Только администратор и менеджер могут управлять прайсом")
    conn = get_db()
    try:
        exists = conn.execute("SELECT id FROM price_categories WHERE id = ?", (payload.category_id,)).fetchone()
        if not exists:
            raise HTTPException(400, "Категория не найдена")
        cur = conn.execute(
            "INSERT INTO price_items (category_id, name, price, unit, sort_order) VALUES (?, ?, ?, ?, ?)",
            (payload.category_id, payload.name, payload.price, payload.unit, payload.sort_order)
        )
        conn.commit()
        return {"ok": True, "id": cur.lastrowid}
    finally:
        conn.close()


@router.put("/items/{item_id}")
def update_item(item_id: int, payload: ItemIn, current_user: dict = Depends(require_auth)) -> dict:
    if current_user["role"] not in ("admin", "manager"):
        raise HTTPException(403, "Только администратор и менеджер могут управлять прайсом")
    conn = get_db()
    try:
        exists = conn.execute("SELECT id FROM price_items WHERE id = ?", (item_id,)).fetchone()
        if not exists:
            raise HTTPException(404, "Позиция не найдена")
        cat = conn.execute("SELECT id FROM price_categories WHERE id = ?", (payload.category_id,)).fetchone()
        if not cat:
            raise HTTPException(400, "Категория не найдена")
        cur = conn.execute(
            "UPDATE price_items SET category_id = ?, name = ?, price = ?, unit = ?, sort_order = ? WHERE id = ?",
            (payload.category_id, payload.name, payload.price, payload.unit, payload.sort_order, item_id)
        )
        conn.commit()
        if not cur.rowcount:
            raise HTTPException(404, "Позиция не найдена")
        return {"ok": True}
    finally:
        conn.close()


@router.delete("/items/{item_id}")
def delete_item(item_id: int, current_user: dict = Depends(require_auth)) -> dict:
    if current_user["role"] not in ("admin", "manager"):
        raise HTTPException(403, "Только администратор и менеджер могут управлять прайсом")
    conn = get_db()
    try:
        cur = conn.execute("DELETE FROM price_items WHERE id = ?", (item_id,))
        conn.commit()
        if not cur.rowcount:
            raise HTTPException(404, "Позиция не найдена")
        return {"ok": True}
    finally:
        conn.close()


@router.get("/export")
def export_prices(current_user: dict = Depends(require_auth)) -> dict:
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT c.name AS category, p.name, p.price, p.unit
            FROM price_items p
            JOIN price_categories c ON c.id = p.category_id
            ORDER BY c.sort_order, p.sort_order, p.name
            """
        ).fetchall()
        csv_lines = ["category,name,price,unit"]
        for r in rows:
            csv_lines.append(f'"{r["category"]}","{r["name"]}","{r["price"]}","{r["unit"]}"')
        return {"csv": "\n".join(csv_lines)}
    finally:
        conn.close()
