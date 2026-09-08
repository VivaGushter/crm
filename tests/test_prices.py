import pytest


def test_list_prices(client, auth_headers, db_conn):
    """Тест: список прайса (категории с позициями)."""
    # Создаём категорию
    db_conn.execute(
        "INSERT INTO price_categories (name, sort_order) VALUES (?, ?)",
        ("Тест Категория", 1)
    )
    db_conn.commit()
    cat_id = db_conn.execute("SELECT id FROM price_categories ORDER BY id DESC LIMIT 1").fetchone()[0]
    
    # Создаём позицию
    db_conn.execute(
        "INSERT INTO price_items (category_id, name, price, unit, sort_order) VALUES (?, ?, ?, ?, ?)",
        (cat_id, "Тест Позиция", "1500", "шт", 1)
    )
    db_conn.commit()
    
    response = client.get("/api/prices", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["name"] == "Тест Категория"
    assert len(data[0]["items"]) >= 1
    assert data[0]["items"][0]["name"] == "Тест Позиция"


def test_create_category(client, auth_headers):
    """Тест: создание категории."""
    payload = {"name": "Новая Категория", "sort_order": 10}
    response = client.post("/api/prices/categories", json=payload, headers=auth_headers)
    assert response.status_code == 200
    
    # Проверяем создание
    response = client.get("/api/prices/categories", headers=auth_headers)
    data = response.json()
    assert any(c["name"] == "Новая Категория" for c in data)


def test_update_category(client, auth_headers, db_conn):
    """Тест: редактирование категории."""
    # Создаём категорию
    db_conn.execute(
        "INSERT INTO price_categories (name, sort_order) VALUES (?, ?)",
        ("Старая Категория", 5)
    )
    db_conn.commit()
    cat_id = db_conn.execute("SELECT id FROM price_categories ORDER BY id DESC LIMIT 1").fetchone()[0]
    
    # Обновляем
    payload = {"name": "Новая Категория", "sort_order": 15}
    response = client.put(f"/api/prices/categories/{cat_id}", json=payload, headers=auth_headers)
    assert response.status_code == 200
    
    # Проверяем обновление
    row = db_conn.execute("SELECT * FROM price_categories WHERE id = ?", (cat_id,)).fetchone()
    assert row["name"] == "Новая Категория"
    assert row["sort_order"] == 15


def test_delete_category(client, auth_headers, db_conn):
    """Тест: удаление категории."""
    # Создаём категорию
    db_conn.execute(
        "INSERT INTO price_categories (name, sort_order) VALUES (?, ?)",
        ("Удалить Категория", 20)
    )
    db_conn.commit()
    cat_id = db_conn.execute("SELECT id FROM price_categories ORDER BY id DESC LIMIT 1").fetchone()[0]
    
    # Удаляем
    response = client.delete(f"/api/prices/categories/{cat_id}", headers=auth_headers)
    assert response.status_code == 200
    
    # Проверяем удаление
    row = db_conn.execute("SELECT id FROM price_categories WHERE id = ?", (cat_id,)).fetchone()
    assert row is None


def test_create_item(client, auth_headers, db_conn):
    """Тест: создание позиции."""
    # Создаём категорию
    db_conn.execute(
        "INSERT INTO price_categories (name, sort_order) VALUES (?, ?)",
        ("Категория Для Позиции", 1)
    )
    db_conn.commit()
    cat_id = db_conn.execute("SELECT id FROM price_categories ORDER BY id DESC LIMIT 1").fetchone()[0]
    
    payload = {
        "category_id": cat_id,
        "name": "Новая Позиция",
        "price": "2500-3500",
        "unit": "м2",
        "sort_order": 5
    }
    response = client.post("/api/prices/items", json=payload, headers=auth_headers)
    assert response.status_code == 200
    
    # Проверяем создание
    row = db_conn.execute("SELECT * FROM price_items WHERE name = 'Новая Позиция'").fetchone()
    assert row is not None
    assert row["price"] == "2500-3500"
    assert row["unit"] == "м2"


def test_update_item(client, auth_headers, db_conn):
    """Тест: редактирование позиции."""
    # Создаём категорию и позицию
    db_conn.execute(
        "INSERT INTO price_categories (name, sort_order) VALUES (?, ?)",
        ("Категория", 1)
    )
    db_conn.commit()
    cat_id = db_conn.execute("SELECT id FROM price_categories ORDER BY id DESC LIMIT 1").fetchone()[0]
    
    db_conn.execute(
        "INSERT INTO price_items (category_id, name, price, unit, sort_order) VALUES (?, ?, ?, ?, ?)",
        (cat_id, "Старая Позиция", "1000", "шт", 1)
    )
    db_conn.commit()
    item_id = db_conn.execute("SELECT id FROM price_items ORDER BY id DESC LIMIT 1").fetchone()[0]
    
    # Обновляем
    payload = {
        "category_id": cat_id,
        "name": "Новая Позиция",
        "price": "2000-3000",
        "unit": "м",
        "sort_order": 10
    }
    response = client.put(f"/api/prices/items/{item_id}", json=payload, headers=auth_headers)
    assert response.status_code == 200
    
    # Проверяем обновление
    row = db_conn.execute("SELECT * FROM price_items WHERE id = ?", (item_id,)).fetchone()
    assert row["name"] == "Новая Позиция"
    assert row["price"] == "2000-3000"
    assert row["unit"] == "м"


def test_delete_item(client, auth_headers, db_conn):
    """Тест: удаление позиции."""
    # Создаём категорию и позицию
    db_conn.execute(
        "INSERT INTO price_categories (name, sort_order) VALUES (?, ?)",
        ("Категория", 1)
    )
    db_conn.commit()
    cat_id = db_conn.execute("SELECT id FROM price_categories ORDER BY id DESC LIMIT 1").fetchone()[0]
    
    db_conn.execute(
        "INSERT INTO price_items (category_id, name, price, unit, sort_order) VALUES (?, ?, ?, ?, ?)",
        (cat_id, "Удалить Позиция", "500", "шт", 1)
    )
    db_conn.commit()
    item_id = db_conn.execute("SELECT id FROM price_items ORDER BY id DESC LIMIT 1").fetchone()[0]
    
    # Удаляем
    response = client.delete(f"/api/prices/items/{item_id}", headers=auth_headers)
    assert response.status_code == 200
    
    # Проверяем удаление
    row = db_conn.execute("SELECT id FROM price_items WHERE id = ?", (item_id,)).fetchone()
    assert row is None
