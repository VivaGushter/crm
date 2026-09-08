from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from backend.db import init_db, create_default_user
from backend.routes import auth, users, permissions, prices, requests

app = FastAPI(title="CRM")

app.mount("/static", StaticFiles(directory="frontend"), name="static")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(permissions.router)
app.include_router(prices.router)
app.include_router(requests.router)


@app.on_event("startup")
def startup_event():
    init_db()
    create_default_user()


@app.get("/")
def read_root(request: Request):
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/prices")
def read_prices(request: Request):
    with open("frontend/price.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/calculator")
def read_calculator(request: Request):
    with open("frontend/calculator.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())
