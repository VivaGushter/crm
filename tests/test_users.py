import pytest
import hashlib


def test_list_users(client, auth_headers):
    """Тест: список пользователей."""
    response = client.get("/api/users", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(u["id"] == "test_admin" for u in data)


def test_create_user(client, auth_headers):
    """Тест: создание пользователя."""
    payload = {
        "id": "new_user",
        "name": "Новый Пользователь",
        "password": "newpass123",
        "role": "user"
    }
    response = client.post("/api/users", json=payload, headers=auth_headers)
    assert response.status_code == 200
    
    # Проверяем, что пользователь создан
    response = client.get("/api/users", headers=auth_headers)
    data = response.json()
    assert any(u["id"] == "new_user" for u in data)


def test_update_user(client, auth_headers, db):
    """Тест: редактирование пользователя."""
    # Создаём пользователя
    password_hash = hashlib.sha256("oldpass".encode("utf-8")).hexdigest()
    db.execute(
        "INSERT INTO users (id, password_hash, name, role, created_at) VALUES (?, ?, ?, ?, ?)",
        ("edit_user", password_hash, "Старое Имя", "user", "2026-01-01T00:00")
    )
    db.commit()
    
    # Обновляем
    payload = {
        "name": "Новое Имя",
        "password": "newpass456",
        "role": "manager"
    }
    response = client.put("/api/users/edit_user", json=payload, headers=auth_headers)
    assert response.status_code == 200
    
    # Проверяем обновление
    row = db.execute("SELECT * FROM users WHERE id = 'edit_user'").fetchone()
    assert row["name"] == "Новое Имя"
    assert row["role"] == "manager"


def test_delete_user(client, auth_headers, db):
    """Тест: удаление пользователя."""
    # Создаём пользователя
    password_hash = hashlib.sha256("delpass".encode("utf-8")).hexdigest()
    db.execute(
        "INSERT INTO users (id, password_hash, name, role, created_at) VALUES (?, ?, ?, ?, ?)",
        ("delete_user", password_hash, "Удалить Пользователь", "user", "2026-01-01T00:00")
    )
    db.commit()
    
    # Удаляем
    response = client.delete("/api/users/delete_user", headers=auth_headers)
    assert response.status_code == 200
    
    # Проверяем удаление
    row = db.execute("SELECT id FROM users WHERE id = 'delete_user'").fetchone()
    assert row is None


def test_create_user_duplicate(client, auth_headers):
    """Тест: создание пользователя с дублирующимся логином."""
    payload = {
        "id": "test_admin",
        "name": "Дубликат",
        "password": "anypassword",
        "role": "user"
    }
    response = client.post("/api/users", json=payload, headers=auth_headers)
    assert response.status_code == 400
    assert "уже существует" in response.json()["detail"]


def test_update_nonexistent_user(client, auth_headers):
    """Тест: редактирование несуществующего пользователя."""
    payload = {"name": "Новое Имя"}
    response = client.put("/api/users/nonexistent", json=payload, headers=auth_headers)
    assert response.status_code == 404
