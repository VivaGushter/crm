import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = "data/crm.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def now_iso() -> str:
    """Return current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def init_db():
    """Initialize database with all required tables and migrations."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        
        # Permissions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                permission TEXT NOT NULL,
                granted_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE(user_id, permission)
            )
        """)
        
        # Price categories table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        
        # Price items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                price TEXT NOT NULL,
                unit TEXT NOT NULL DEFAULT 'шт',
                is_active INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (category_id) REFERENCES price_categories(id) ON DELETE CASCADE
            )
        """)
        
        # Requests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                visit_date TEXT,
                address TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                price REAL,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        
        # Audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id INTEGER,
                details TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """)
        
        # === v2.1 Calculator Migration ===
        # Add financial fields to requests
        cursor.execute("""
            ALTER TABLE requests ADD COLUMN work_amount REAL NOT NULL DEFAULT 0
        """)
        cursor.execute("""
            ALTER TABLE requests ADD COLUMN discount_type TEXT NOT NULL DEFAULT 'none'
        """)
        cursor.execute("""
            ALTER TABLE requests ADD COLUMN discount_value REAL NOT NULL DEFAULT 0
        """)
        cursor.execute("""
            ALTER TABLE requests ADD COLUMN discount_amount REAL NOT NULL DEFAULT 0
        """)
        cursor.execute("""
            ALTER TABLE requests ADD COLUMN materials_amount REAL NOT NULL DEFAULT 0
        """)
        
        # Create request_calculation_items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS request_calculation_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id INTEGER NOT NULL,
                price_item_id INTEGER,
                category_name_snapshot TEXT NOT NULL DEFAULT '',
                name_snapshot TEXT NOT NULL,
                unit_snapshot TEXT NOT NULL DEFAULT 'шт',
                unit_price REAL NOT NULL DEFAULT 0,
                quantity REAL NOT NULL DEFAULT 1,
                line_total REAL NOT NULL DEFAULT 0,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()

def create_default_user():
    """Create default admin user if not exists."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", ("admin",))
        if not cursor.fetchone():
            import bcrypt
            password_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
            cursor.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                ("admin", password_hash, "admin")
            )
            conn.commit()
