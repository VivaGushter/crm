from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "crm.db"

STATUSES = {
    "new": "Новая",
    "scheduled": "Назначена",
    "work": "В работе",
    "done": "Завершена",
    "cancel": "Отменена",
}

SOURCES = {
    "unknown": "Не указан",
    "avito": "Авито",
    "house_chats": "Домовые чаты",
}

CONTACT_METHODS = {
    "": "Не указано",
    "avito": "Авито",
    "phone": "Звонок",
    "telegram": "Telegram",
    "max": "Max",
}

ACTIVE_STATUSES = {"new", "scheduled", "work"}
