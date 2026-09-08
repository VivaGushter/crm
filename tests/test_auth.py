import pytest
from backend.sessions import get_session


def test_login_success(client, test_user):
    """Тест: успешный вход."""
    response = client.post(
        "/api/auth/login",
        json={"username": test_user["id"], "password": test_user["password"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert data["user"]["id"] == test_user["id"]
    assert data["user"]["role"] == "admin"


def test_login_invalid_password(client, test_user):
    """Тест: неверный пароль."""
    response = client.post(
        "/api/auth/login",
        json={"username": test_user["id"], "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "Неверный логин или пароль" in response.json()["detail"]


def test_login_nonexistent_user(client):
    """Тест: пользователь не существует."""
    response = client.post(
        "/api/auth/login",
        json={"username": "nonexistent", "password": "anypassword"}
    )
    assert response.status_code == 401


def test_logout(client, auth_token, test_user):
    """Тест: выход (удаление сессии)."""
    # Проверяем, что токен работает
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    
    # Выход
    response = client.post("/api/auth/logout", headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 200
    
    # Токен больше не работает
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {auth_token}"})
    assert response.status_code == 401


def test_me_endpoint(client, auth_headers, test_user):
    """Тест: получение текущего пользователя."""
    response = client.get("/api/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_user["id"]
    assert data["role"] == "admin"


def test_unauthorized_request(client):
    """Тест: запрос без авторизации."""
    response = client.get("/api/requests")
    assert response.status_code == 401


def test_invalid_token(client):
    """Тест: невалидный токен."""
    response = client.get(
        "/api/requests",
        headers={"Authorization": "Bearer invalidtoken123"}
    )
    assert response.status_code == 401
