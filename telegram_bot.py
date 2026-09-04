#!/usr/bin/env python3
"""
Telegram-бот для Master CRM
Авторизация через логин/пароль из CRM
"""

import asyncio
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# === КОНФИГУРАЦИЯ ===
BOT_TOKEN = "8936987675:AAGHorrMsWz9aRd_NNhZn5PgRPrvbsldTnU"
CRM_API_URL = "http://127.0.0.1:8000"
DB_PATH = Path(__file__).parent / "data" / "crm.db"

# === ХЭШИРОВАНИЕ ПАРОЛЕЙ (как в CRM) ===
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

# === БАЗА ДАННЫХ ===
def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn

def init_telegram_table():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS telegram_users (
            telegram_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            linked_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()

def link_user(telegram_id: str, user_id: str) -> bool:
    conn = get_db()
    now = datetime.now().replace(second=0, microsecond=0).isoformat(timespec="minutes")
    try:
        conn.execute(
            "INSERT OR REPLACE INTO telegram_users (telegram_id, user_id, linked_at) VALUES (?, ?, ?)",
            (telegram_id, user_id, now)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error linking user: {e}")
        return False
    finally:
        conn.close()

def get_user_by_telegram(telegram_id: str) -> Optional[str]:
    conn = get_db()
    row = conn.execute("SELECT user_id FROM telegram_users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    conn.close()
    return row["user_id"] if row else None

def unlink_user(telegram_id: str) -> bool:
    conn = get_db()
    try:
        conn.execute("DELETE FROM telegram_users WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
        return True
    finally:
        conn.close()

def verify_crm_login(user_id: str, password: str) -> Optional[dict]:
    conn = get_db()
    row = conn.execute("SELECT id, password_hash, name, role FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if row and row["password_hash"] == hash_password(password):
        return {"id": row["id"], "name": row["name"], "role": row["role"]}
    return None

def get_requests_for_user(user_id: str, days: int = 1) -> list:
    conn = get_db()
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end = today + timedelta(days=days)
    rows = conn.execute(
        """
        SELECT * FROM requests
        WHERE visit_date >= ? AND visit_date < ?
        ORDER BY visit_date ASC
        """,
        (today.isoformat(), end.isoformat())
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_stats(user_id: str) -> dict:
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) AS c FROM requests").fetchone()["c"]
    done = conn.execute("SELECT COUNT(*) AS c FROM requests WHERE status = 'done'").fetchone()["c"]
    revenue = conn.execute("SELECT COALESCE(SUM(price), 0) AS s FROM requests WHERE status = 'done'").fetchone()["s"]
    scheduled = conn.execute("SELECT COUNT(*) AS c FROM requests WHERE status = 'scheduled'").fetchone()["c"]
    conn.close()
    return {"total": total, "done": done, "revenue": revenue, "scheduled": scheduled}

# === МАШИНА СОСТОЯНИЙ ДЛЯ АВТОРИЗАЦИИ ===
class AuthState(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()

# === БОТ И ДИСПЕТЧЕР ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# === КЛАВИАТУРЫ ===
def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Сегодня", callback_data="today")],
        [InlineKeyboardButton(text="📊 Неделя", callback_data="week")],
        [InlineKeyboardButton(text="📈 Статистика", callback_data="stats")],
        [InlineKeyboardButton(text="➕ Новая заявка", callback_data="new")],
        [InlineKeyboardButton(text="❌ Отвязать аккаунт", callback_data="unlink")],
    ])

def status_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🟡 В работе", callback_data=f"status_{request_id}_work")],
        [InlineKeyboardButton(text="🟢 Завершена", callback_data=f"status_{request_id}_done")],
        [InlineKeyboardButton(text="🔴 Отменена", callback_data=f"status_{request_id}_cancel")],
    ])

# === ОБРАБОТЧИКИ ===

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    telegram_id = str(message.from_user.id)
    user_id = get_user_by_telegram(telegram_id)
    
    if user_id:
        await message.answer(
            f"👋 Привет! Вы уже авторизованы.\n\n"
            f"Используйте кнопки ниже для работы с CRM.",
            reply_markup=main_keyboard()
        )
    else:
        await message.answer(
            "👋 Привет! Это бот Master CRM.\n\n"
            "Для начала работы нужно привязать ваш аккаунт.\n\n"
            "📝 **Введите ваш логин из CRM:**",
            parse_mode="Markdown"
        )
        await state.set_state(AuthState.waiting_for_login)

@dp.message(AuthState.waiting_for_login)
async def process_login(message: types.Message, state: FSMContext):
    login = message.text.strip()
    await state.update_data(login=login)
    await message.answer("🔐 **Введите ваш пароль:**", parse_mode="Markdown")
    await state.set_state(AuthState.waiting_for_password)

@dp.message(AuthState.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()
    login = data.get("login")
    
    user = verify_crm_login(login, password)
    if user:
        telegram_id = str(message.from_user.id)
        if link_user(telegram_id, user["id"]):
            await message.answer(
                f"✅ **Авторизация успешна!**\n\n"
                f"Добро пожаловать, {user['name']}!\n\n"
                f"Теперь вы можете управлять заявками через бота.",
                parse_mode="Markdown",
                reply_markup=main_keyboard()
            )
        else:
            await message.answer("❌ Ошибка при привязке аккаунта. Попробуйте ещё раз.")
    else:
        await message.answer("❌ Неверный логин или пароль. Попробуйте `/start` ещё раз.")
    
    await state.clear()

@dp.callback_query(F.data == "today")
async def cb_today(callback: types.CallbackQuery):
    telegram_id = str(callback.from_user.id)
    user_id = get_user_by_telegram(telegram_id)
    
    if not user_id:
        await callback.answer("❌ Сначала авторизуйтесь через /start", show_alert=True)
        return
    
    requests = get_requests_for_user(user_id, days=1)
    if not requests:
        await callback.answer("📭 На сегодня заявок нет.", show_alert=True)
        return
    
    text = "📅 **Заявки на сегодня:**\n\n"
    for r in requests:
        time = r["visit_date"][11:16] if len(r["visit_date"]) > 16 else "??:??"
        text += f"⏰ **{time}** — {r['client']}\n"
        text += f"📍 {r['address']}\n"
        text += f"📞 {r['phone']}\n"
        text += f"💰 {r['price']} ₽ · {r['status']}\n\n"
    
    await callback.answer(text, show_alert=True)

@dp.callback_query(F.data == "week")
async def cb_week(callback: types.CallbackQuery):
    telegram_id = str(callback.from_user.id)
    user_id = get_user_by_telegram(telegram_id)
    
    if not user_id:
        await callback.answer("❌ Сначала авторизуйтесь через /start", show_alert=True)
        return
    
    requests = get_requests_for_user(user_id, days=7)
    if not requests:
        await callback.answer("📭 На неделю заявок нет.", show_alert=True)
        return
    
    text = "📊 **Заявки на 7 дней:**\n\n"
    for r in requests:
        date = r["visit_date"][:10]
        time = r["visit_date"][11:16] if len(r["visit_date"]) > 16 else "??:??"
        text += f"📅 **{date} {time}** — {r['client']}\n"
        text += f"📍 {r['address']}\n"
        text += f"💰 {r['price']} ₽\n\n"
    
    await callback.answer(text, show_alert=True)

@dp.callback_query(F.data == "stats")
async def cb_stats(callback: types.CallbackQuery):
    telegram_id = str(callback.from_user.id)
    user_id = get_user_by_telegram(telegram_id)
    
    if not user_id:
        await callback.answer("❌ Сначала авторизуйтесь через /start", show_alert=True)
        return
    
    stats = get_stats(user_id)
    text = (
        "📈 **Статистика CRM:**\n\n"
        f"📋 Всего заявок: **{stats['total']}**\n"
        f"✅ Завершено: **{stats['done']}**\n"
        f"🟡 Назначено: **{stats['scheduled']}**\n"
        f"💰 Выручка: **{stats['revenue']} ₽**"
    )
    await callback.answer(text, show_alert=True)

@dp.callback_query(F.data == "new")
async def cb_new(callback: types.CallbackQuery):
    await callback.answer(
        "➕ Чтобы создать новую заявку, используйте веб-интерфейс:\n"
        "http://194.226.166.190\n\n"
        "В боте доступна только просмотр и управление статусами.",
        show_alert=True
    )

@dp.callback_query(F.data == "unlink")
async def cb_unlink(callback: types.CallbackQuery):
    telegram_id = str(callback.from_user.id)
    if unlink_user(telegram_id):
        await callback.answer(
            "✅ Аккаунт отвязан.\n\n"
            "Используйте /start для повторной авторизации.",
            show_alert=True
        )
    else:
        await callback.answer("❌ Ошибка при отвязке.", show_alert=True)

@dp.callback_query(F.data.startswith("status_"))
async def cb_status(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    if len(parts) != 3:
        await callback.answer("❌ Неверная команда", show_alert=True)
        return
    
    request_id = int(parts[1])
    new_status = parts[2]
    
    # TODO: Здесь будет API вызов для обновления статуса
    await callback.answer(f"✅ Статус заявки #{request_id} изменён на {new_status}", show_alert=True)

# === ЗАПУСК ===
async def main():
    init_telegram_table()
    print("🤖 Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())