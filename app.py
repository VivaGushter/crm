import os
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend.db import init_db, get_db, now_iso
from backend.auth import get_current_user, require_auth, verify_password, hash_password
from backend.sessions import create_session, delete_session

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(FRONTEND_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app = FastAPI(title="Master CRM")

from backend.routes import reports, requests, users, settings, prices, admin

app.include_router(reports.router)
app.include_router(requests.router)
app.include_router(users.router)
app.include_router(settings.router)
app.include_router(prices.router)
app.include_router(admin.router)


class LoginIn(BaseModel):
    username: str
    password: str


class LoginOut(BaseModel):
    token: str
    user: dict


def get_bearer_token(request: Request) -> str:
    """Извлечь Bearer токен из заголовка Authorization."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return ""
    return auth[7:]


@app.post("/api/auth/login", response_model=LoginOut)
def login(payload: LoginIn):
    """Вход: логин + пароль → токен + пользователь."""
    conn = get_db()
    try:
        user = conn.execute(
            "SELECT id, password_hash, name, role, theme, can_edit_price, can_edit_requests, can_delete_requests FROM users WHERE id = ?",
            (payload.username,)
        ).fetchone()
        if not user or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")
        token = create_session(user["id"])
        user_dict = {
            "id": user["id"],
            "name": user["name"],
            "role": user["role"],
            "theme": user["theme"],
            "can_edit_price": bool(user["can_edit_price"]),
            "can_edit_requests": bool(user["can_edit_requests"]),
            "can_delete_requests": bool(user["can_delete_requests"]),
        }
        return LoginOut(token=token, user=user_dict)
    finally:
        conn.close()


@app.post("/api/auth/logout")
def logout(request: Request):
    """Выход: удалить сессию."""
    token = get_bearer_token(request)
    if token:
        delete_session(token)
    return {"ok": True}


@app.get("/api/auth/me")
def me(current_user: dict = Depends(require_auth)):
    """Получить текущего пользователя по токену."""
    return current_user


@app.get("/")
def index():
    path = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="frontend/index.html not found")
    return FileResponse(path, media_type="text/html")


@app.get("/price")
def price_page():
    path = os.path.join(FRONTEND_DIR, "price.html")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="frontend/price.html not found")
    return FileResponse(path, media_type="text/html")


@app.get("/admin")
def admin_page():
    path = os.path.join(FRONTEND_DIR, "admin.html")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="frontend/admin.html not found")
    return FileResponse(path, media_type="text/html")


@app.get("/calculation")
def calculation_page():
    path = os.path.join(FRONTEND_DIR, "calculation.html")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="frontend/calculation.html not found")
    return FileResponse(path, media_type="text/html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def startup():
    init_db()
