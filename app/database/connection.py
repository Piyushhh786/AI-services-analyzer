import os
import sqlite3
import json
from contextlib import contextmanager
from typing import Generator, Any
from app.core.config import settings
from app.core.logging import logger

try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False


class DatabaseConnection:
    def __init__(self):
        self.db_url = settings.DATABASE_URL
        self.is_postgres = False
        self._test_connection()

    def _test_connection(self):
        if self.db_url and PSYCOPG_AVAILABLE:
            try:
                with psycopg.connect(self.db_url, connect_timeout=5) as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1;")
                self.is_postgres = True
                logger.info("Connected to PostgreSQL database successfully.")
                self.init_db()
                return
            except Exception as e:
                logger.warning(f"Could not connect to PostgreSQL ({e}). Falling back to local SQLite database.")
        
        self.is_postgres = False
        self.sqlite_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "analyzer_local.db")
        logger.info(f"Using SQLite database at {self.sqlite_path}")
        self.init_db()

    def init_db(self):
        """Initializes tables in PostgreSQL or SQLite."""
        if self.is_postgres:
            schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
            if os.path.exists(schema_path):
                with open(schema_path, "r", encoding="utf-8") as f:
                    schema_sql = f.read()
                with self.get_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(schema_sql)
                    conn.commit()
                logger.info("PostgreSQL schema initialized.")
        else:
            with sqlite3.connect(self.sqlite_path) as conn:
                cur = conn.cursor()
                cur.execute("""
                CREATE TABLE IF NOT EXISTS upload_sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                );
                """)
                cur.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    transaction_date TIMESTAMP NOT NULL,
                    merchant TEXT NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    amount REAL NOT NULL,
                    type TEXT NOT NULL,
                    extra_data TEXT DEFAULT '{}',
                    FOREIGN KEY (session_id) REFERENCES upload_sessions(session_id) ON DELETE CASCADE
                );
                """)
                cur.execute("CREATE INDEX IF NOT EXISTS idx_transactions_session_id ON transactions(session_id);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(session_id, transaction_date);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(session_id, category);")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(session_id, type);")
                conn.commit()
            logger.info("SQLite schema initialized.")

    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        if self.is_postgres:
            conn = psycopg.connect(self.db_url, row_factory=dict_row)
            try:
                yield conn
            finally:
                conn.close()
        else:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()


db = DatabaseConnection()
