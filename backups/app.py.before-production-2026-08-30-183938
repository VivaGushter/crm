import os

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.db import init_db
from backend.routes import reports, requests, users
from backend.auth import get_current_user

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(FRONTEND_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app = FastAPI(title="Master CRM")

# В каждом router уже указан собственный путь /api/...
app.include_router(reports.router)
app.include_router(requests.router)
app.include_router(users.router)


@app.get("/")
def index():
    path = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.isfile(path):
        raise HTTPException(
            status_code=404,
            detail="frontend/index.html not found",
        )
    return FileResponse(path, media_type="text/html")


@app.get("/api/me")
def me(current_user: dict = Depends(get_current_user)):
   return current_user
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def startup():
    init_db()
