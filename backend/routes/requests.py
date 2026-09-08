from fastapi import APIRouter, HTTPException, Depends
from typing import List
from backend.db import get_db
from backend.schemas import RequestCreate, RequestUpdate, Request, CalculationItem
from backend.auth import get_current_user
import json
import math

router = APIRouter(prefix="/api/requests", tags=["requests"])

VALID_DISCOUNT_TYPES = {"none", "percent", "rubles"}
PIECE_UNITS = {"шт", "шт."}


def validate_calculation(payload: RequestCreate | RequestUpdate):
    """Validate calculator data and calculate trustworthy totals on the server."""
    discount_type = payload.discount_type or "none"
    if discount_type not in VALID_DISCOUNT_TYPES:
        raise HTTPException(status_code=422, detail="Недопустимый тип скидки")

    materials = float(payload.materials_amount or 0)
    if materials < 0:
        raise HTTPException(status_code=422, detail="Сумма материалов не может быть отрицательной")

    items = payload.calculation_items
    if items is None:
        return None

    work_amount = 0.0
    normalized_items = []
    for position, item in enumerate(items):
        quantity = float(item.quantity)
        unit_price = float(item.unit_price)
        if quantity <= 0:
            raise HTTPException(status_code=422, detail=f"Количество для «{item.name_snapshot}» должно быть больше нуля")
        if item.unit_snapshot.strip().lower() in PIECE_UNITS and not quantity.is_integer():
            raise HTTPException(status_code=422, detail=f"Для «{item.name_snapshot}» в штуках допускается только целое количество")
        if unit_price < 0:
            raise HTTPException(status_code=422, detail=f"Цена для «{item.name_snapshot}» не может быть отрицательной")

        line_total = round(quantity * unit_price, 2)
        work_amount += line_total
        normalized_items.append({
            "price_item_id": item.price_item_id,
            "category_name_snapshot": item.category_name_snapshot,
            "name_snapshot": item.name_snapshot,
            "unit_snapshot": item.unit_snapshot,
            "unit_price": unit_price,
            "quantity": quantity,
            "line_total": line_total,
            "sort_order": position,
        })

    work_amount = round(work_amount, 2)
    discount_value = float(payload.discount_value or 0)
    if discount_value < 0:
        raise HTTPException(status_code=422, detail="Скидка не может быть отрицательной")
    if discount_type == "percent" and discount_value > 100:
        raise HTTPException(status_code=422, detail="Скидка в процентах не может превышать 100%")

    if discount_type == "percent":
        discount_amount = round(work_amount * discount_value / 100, 2)
    elif discount_type == "rubles":
        discount_amount = min(round(discount_value, 2), work_amount)
    else:
        discount_value = 0.0
        discount_amount = 0.0

    return {
        "items": normalized_items,
        "work_amount": work_amount,
        "discount_type": discount_type,
        "discount_value": discount_value,
        "discount_amount": discount_amount,
        "materials_amount": round(materials, 2),
        "price": round(work_amount - discount_amount + materials, 2),
    }


def save_calculation_items(cursor, request_id: int, items: list):
    cursor.execute("DELETE FROM request_calculation_items WHERE request_id = ?", (request_id,))
    for item in items:
        cursor.execute("""
            INSERT INTO request_calculation_items (
                request_id, price_item_id, category_name_snapshot, name_snapshot,
                unit_snapshot, unit_price, quantity, line_total, sort_order
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request_id, item["price_item_id"], item["category_name_snapshot"],
            item["name_snapshot"], item["unit_snapshot"], item["unit_price"],
            item["quantity"], item["line_total"], item["sort_order"]
        ))


def row_to_dict(row):
    return dict(row) if row else None


@router.get("", response_model=List[Request])
def get_requests(current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM requests ORDER BY visit_date DESC, created_at DESC")
        return [row_to_dict(row) for row in cursor.fetchall()]


@router.get("/{request_id}", response_model=Request)
def get_request(request_id: int, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM requests WHERE id = ?", (request_id,))
        request = row_to_dict(cursor.fetchone())
        if not request:
            raise HTTPException(status_code=404, detail="Заявка не найдена")
        return request


@router.get("/{request_id}/calculation", response_model=List[CalculationItem])
def get_request_calculation(request_id: int, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM requests WHERE id = ?", (request_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Заявка не найдена")
        cursor.execute("""
            SELECT * FROM request_calculation_items
            WHERE request_id = ?
            ORDER BY sort_order, id
        """, (request_id,))
        return [row_to_dict(row) for row in cursor.fetchall()]


@router.post("", response_model=Request, status_code=201)
def create_request(data: RequestCreate, current_user: dict = Depends(get_current_user)):
    calculation = validate_calculation(data)
    with get_db() as conn:
        cursor = conn.cursor()
        if calculation:
            cursor.execute("""
                INSERT INTO requests (
                    client_name, phone, visit_date, address, status, price, notes,
                    work_amount, discount_type, discount_value, discount_amount, materials_amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.client_name, data.phone, data.visit_date, data.address, data.status,
                calculation["price"], data.notes, calculation["work_amount"],
                calculation["discount_type"], calculation["discount_value"],
                calculation["discount_amount"], calculation["materials_amount"]
            ))
        else:
            cursor.execute("""
                INSERT INTO requests (client_name, phone, visit_date, address, status, price, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (data.client_name, data.phone, data.visit_date, data.address, data.status, data.price, data.notes))
        request_id = cursor.lastrowid

        if calculation:
            save_calculation_items(cursor, request_id, calculation["items"])
        cursor.execute("""
            INSERT INTO audit_log (user_id, action, entity_type, entity_id, details)
            VALUES (?, 'create', 'request', ?, ?)
        """, (current_user["id"], request_id, json.dumps({"calculator": bool(calculation)}, ensure_ascii=False)))
        conn.commit()
        cursor.execute("SELECT * FROM requests WHERE id = ?", (request_id,))
        return row_to_dict(cursor.fetchone())


@router.put("/{request_id}", response_model=Request)
def update_request(request_id: int, data: RequestUpdate, current_user: dict = Depends(get_current_user)):
    calculation = validate_calculation(data)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM requests WHERE id = ?", (request_id,))
        existing = row_to_dict(cursor.fetchone())
        if not existing:
            raise HTTPException(status_code=404, detail="Заявка не найдена")

        updates = data.model_dump(exclude_unset=True, exclude={"calculation_items"})
        if calculation:
            updates.update({
                "price": calculation["price"],
                "work_amount": calculation["work_amount"],
                "discount_type": calculation["discount_type"],
                "discount_value": calculation["discount_value"],
                "discount_amount": calculation["discount_amount"],
                "materials_amount": calculation["materials_amount"],
            })
        if updates:
            set_clause = ", ".join(f"{field} = ?" for field in updates)
            values = list(updates.values()) + [request_id]
            cursor.execute(f"UPDATE requests SET {set_clause}, updated_at = datetime('now') WHERE id = ?", values)
        if calculation:
            save_calculation_items(cursor, request_id, calculation["items"])

        cursor.execute("""
            INSERT INTO audit_log (user_id, action, entity_type, entity_id, details)
            VALUES (?, 'update', 'request', ?, ?)
        """, (current_user["id"], request_id, json.dumps({"calculator": bool(calculation)}, ensure_ascii=False)))
        conn.commit()
        cursor.execute("SELECT * FROM requests WHERE id = ?", (request_id,))
        return row_to_dict(cursor.fetchone())


@router.delete("/{request_id}", status_code=204)
def delete_request(request_id: int, current_user: dict = Depends(get_current_user)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM requests WHERE id = ?", (request_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Заявка не найдена")
        cursor.execute("DELETE FROM requests WHERE id = ?", (request_id,))
        cursor.execute("""
            INSERT INTO audit_log (user_id, action, entity_type, entity_id, details)
            VALUES (?, 'delete', 'request', ?, ?)
        """, (current_user["id"], request_id, "{}"))
        conn.commit()
