import pytest
from datetime import datetime


def test_create_request(client, auth_headers):
    """Тест: создание заявки."""
    payload = {
        "client": "Иван Иванов",
        "visit_date": "2026-09-10T14:00",
        "address": "ул. Ленина, д. 1",
        "phone": "+79991234567",
        "status": "new",
        "price": 1500,
        "comment": "Тестовая заявка",
        "assignee": "test_admin",
        "source": "avito",
        "contact_method": "phone"
    }
    response = client.post("/api/requests", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert "id" in data


def test_list_requests(client, auth_headers, db):
    """Тест: список заявок."""
    # Создаём тестовую заявку
    db.execute(
        """
        INSERT INTO requests (client, visit_date, address, phone, status, price, assignee, created_by, updated_at, source, contact_method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("Тест Клиент", "2026-09-15T10:00", "ул. Тестовая, 1", "+79990000000", "new", 1000, "test_admin", "test_admin", "2026-09-08T12:00", "avito", "phone")
    )
    db.commit()
    
    response = client.get("/api/requests", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["client"] == "Тест Клиент"


def test_update_request(client, auth_headers, db):
    """Тест: редактирование заявки."""
    # Создаём заявку
    db.execute(
        """
        INSERT INTO requests (client, visit_date, address, phone, status, price, assignee, created_by, updated_at, source, contact_method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("Клиент До", "2026-09-12T11:00", "ул. Старая, 5", "+79991111111", "scheduled", 2000, "test_admin", "test_admin", "2026-09-08T12:00", "house_chats", "telegram")
    )
    db.commit()
    request_id = db.execute("SELECT id FROM requests ORDER BY id DESC LIMIT 1").fetchone()[0]
    
    # Обновляем
    payload = {
        "client": "Клиент После",
        "visit_date": "2026-09-12T11:00",
        "address": "ул. Новая, 10",
        "phone": "+79992222222",
        "status": "work",
        "price": 2500,
        "comment": "Обновлено",
        "assignee": "test_admin",
        "source": "avito",
        "contact_method": "phone"
    }
    response = client.put(f"/api/requests/{request_id}", json=payload, headers=auth_headers)
    assert response.status_code == 200
    
    # Проверяем обновление
    row = db.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
    assert row["client"] == "Клиент После"
    assert row["status"] == "work"
    assert row["price"] == 2500


def test_delete_request(client, auth_headers, db):
    """Тест: удаление заявки (только admin/manager)."""
    # Создаём заявку
    db.execute(
        """
        INSERT INTO requests (client, visit_date, address, phone, status, price, assignee, created_by, updated_at, source, contact_method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("Удалить Клиент", "2026-09-20T15:00", "ул. Удаляемая, 3", "+79993333333", "new", 500, "test_admin", "test_admin", "2026-09-08T12:00", "unknown", "")
    )
    db.commit()
    request_id = db.execute("SELECT id FROM requests ORDER BY id DESC LIMIT 1").fetchone()[0]
    
    # Удаляем
    response = client.delete(f"/api/requests/{request_id}", headers=auth_headers)
    assert response.status_code == 200
    
    # Проверяем удаление
    row = db.execute("SELECT id FROM requests WHERE id = ?", (request_id,)).fetchone()
    assert row is None


def test_filter_requests(client, auth_headers, db):
    """Тест: фильтрация заявок по статусу."""
    # Создаём две заявки с разными статусами
    db.execute(
        """
        INSERT INTO requests (client, visit_date, address, phone, status, price, assignee, created_by, updated_at, source, contact_method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("Клиент 1", "2026-09-10T10:00", "ул. 1", "+79990000001", "new", 1000, "test_admin", "test_admin", "2026-09-08T12:00", "avito", "phone")
    )
    db.execute(
        """
        INSERT INTO requests (client, visit_date, address, phone, status, price, assignee, created_by, updated_at, source, contact_method)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        ("Клиент 2", "2026-09-11T11:00", "ул. 2", "+79990000002", "done", 2000, "test_admin", "test_admin", "2026-09-08T12:00", "avito", "phone")
    )
    db.commit()
    
    # Фильтр по статусу "done"
    response = client.get("/api/requests?status=done", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == "done"
