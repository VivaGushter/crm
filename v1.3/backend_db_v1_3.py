import sqlite3
from datetime import datetime

from .config import DATA_DIR, DB_PATH


def get_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


def table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})")}


def now_iso() -> str:
    return datetime.now().replace(second=0, microsecond=0).isoformat(timespec="minutes")


def init_db() -> None:
    conn = get_db()
    try:
        # Таблица пользователей с ролью manager
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL,
                theme TEXT NOT NULL DEFAULT 'light'
            )
            """
        )
        
        # Таблица заявок
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client TEXT NOT NULL,
                visit_date TEXT NOT NULL,
                address TEXT NOT NULL,
                phone TEXT NOT NULL,
                status TEXT NOT NULL,
                price REAL NOT NULL DEFAULT 0,
                comment TEXT,
                assignee TEXT NOT NULL,
                created_by TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT '',
                source TEXT NOT NULL DEFAULT 'unknown',
                contact_method TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (assignee) REFERENCES users(id)
            )
            """
        )

        # Миграции для requests
        columns = table_columns(conn, "requests")
        migrations = {
            "created_by": "ALTER TABLE requests ADD COLUMN created_by TEXT NOT NULL DEFAULT ''",
            "updated_at": "ALTER TABLE requests ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''",
            "source": "ALTER TABLE requests ADD COLUMN source TEXT NOT NULL DEFAULT 'unknown'",
            "contact_method": "ALTER TABLE requests ADD COLUMN contact_method TEXT NOT NULL DEFAULT ''",
        }
        for column, sql in migrations.items():
            if column not in columns:
                conn.execute(sql)

        # Миграции для users
        user_columns = table_columns(conn, "users")
        if "theme" not in user_columns:
            conn.execute("ALTER TABLE users ADD COLUMN theme TEXT NOT NULL DEFAULT 'light'")

        # Аудит-лог
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                old_values TEXT,
                new_values TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        # Старые данные
        now = now_iso()
        conn.execute("UPDATE requests SET assignee = 'rus' WHERE assignee = 'master1'")
        conn.execute("UPDATE requests SET assignee = 'Gushter' WHERE assignee = 'master2'")
        conn.execute("UPDATE requests SET assignee = 'rus' WHERE assignee IS NULL OR assignee = ''")
        conn.execute("UPDATE requests SET created_by = assignee WHERE created_by IS NULL OR created_by = ''")
        conn.execute("UPDATE requests SET updated_at = ? WHERE updated_at IS NULL OR updated_at = ''", (now,))
        conn.execute("UPDATE requests SET source = 'unknown' WHERE source IS NULL OR source = ''")
        conn.execute("UPDATE requests SET contact_method = '' WHERE contact_method IS NULL")

        conn.commit()
    finally:
        conn.close()