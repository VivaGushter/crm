import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from backend.db import get_db, init_db
from backend.auth import get_current_user
from backend.routes import reports, requests, users

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(FRONTEND_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app = FastAPI()

app.include_router(reports.router, prefix="/api", tags=["reports"])
app.include_router(requests.router, prefix="/api", tags=["requests"])
app.include_router(users.router, prefix="/api", tags=["users"])

security = HTTPBasic()


def _verify_user(db, username: str, password: str) -> Optional[dict]:
    cur = db.cursor()
    cur.execute("SELECT id, name, password_hash, role FROM users WHERE id = ?", (username,))
    row = cur.fetchone()
    if not row:
        return None
    uid, name, password_hash, role = row
    import hashlib
    if hashlib.sha256(password.encode("utf-8")).hexdigest() != password_hash:
        return None
    return {"id": uid, "name": name, "role": role}


@app.post("/api/login")
async def login(request: Request, db=Depends(get_db)):
    try:
        data = request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password required")
    user = _verify_user(db, username, password)
    if not user:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    # Simple token: random hex, stored only in memory for this session
    token = secrets.token_hex(16)
    # In this minimal version we do not persist tokens; frontend just keeps it
    return {"user": user, "token": token}


@app.get("/api/me")
def me(current_user=Depends(get_current_user)):
    return current_user


@app.get("/")
def index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="frontend/index.html not found")
    return FileResponse(index_path, media_type="text/html")


app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=8001)
