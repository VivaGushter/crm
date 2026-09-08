import os
import sys
import pytest
from fastapi.testclient import TestClient

# Добавляем корень проекта в sys.path для импортов
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.db import get_db, init_db, DB_PATH
from backend.sessions import create_session, delete_all_user_sessions
from app import app


TEST_DB_PATH = ":memory:"


@pytest.fixture(scope="function")
def db(monkeypatch):
    """Фикстура: тестовая БД в памяти."""
    monkeypatch.setattr("backend.db.DB_PATH", TEST_DB_PATH)
    monkeypatch.setattr("backend.config.DB_PATH", TEST_DB_PATH)
    init_db()
    conn = get_db()
    yield conn
    conn.close()


@pytest.fixture(scope="function")
def client(db):
    """Фикстура: TestClient для FastAPI."""
    return TestClient(app)


@pytest.fixture(scope="function")
def test_user(db):
    """Фикстура: тестовый пользователь admin."""
    import hashlib
    user_id = "test_admin"
    password = "testpass123"
    password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    db.execute(
        "INSERT INTO users (id, password_hash, name, role, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, password_hash, "Test Admin", "admin", "2026-01-01T00:00")
    )
    db.commit()
    return {"id": user_id, "password": password}


@pytest.fixture(scope="function")
def auth_token(client, test_user):
    """Фикстура: Bearer токен для тестового пользователя."""
    response = client.post(
        "/api/auth/login",
        json={"username": test_user["id"], "password": test_user["password"]}
    )
    assert response.status_code == 200
    token = response.json()["token"]
    yield token
    delete_all_user_sessions(test_user["id"])


@pytest.fixture(scope="function")
def auth_headers(auth_token):
    """Фикстура: заголовки Authorization для запросов."""
    return {"Authorization": f"Bearer {auth_token}"}
