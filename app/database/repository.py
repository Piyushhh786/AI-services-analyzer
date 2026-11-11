import json
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from app.database.connection import db
from app.database.models import UploadSessionModel, TransactionModel
from app.core.logging import logger


def parse_db_datetime(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            try:
                return datetime.strptime(val[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


class DatabaseRepository:
    def __init__(self):
        self.db = db

    def create_session(self, session_id: str, ttl_minutes: int = 30) -> UploadSessionModel:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=ttl_minutes)
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            query = """
            INSERT INTO upload_sessions (session_id, created_at, expires_at, last_activity, status)
            VALUES (%s, %s, %s, %s, %s)
            """ if self.db.is_postgres else """
            INSERT INTO upload_sessions (session_id, created_at, expires_at, last_activity, status)
            VALUES (?, ?, ?, ?, ?)
            """
            cur.execute(query, (session_id, now.isoformat(), expires_at.isoformat(), now.isoformat(), "active"))
            conn.commit()

        return UploadSessionModel(
            session_id=session_id,
            created_at=now,
            expires_at=expires_at,
            last_activity=now,
            status="active"
        )

    def get_session(self, session_id: str) -> Optional[UploadSessionModel]:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            query = "SELECT session_id, created_at, expires_at, last_activity, status FROM upload_sessions WHERE session_id = %s" if self.db.is_postgres else "SELECT session_id, created_at, expires_at, last_activity, status FROM upload_sessions WHERE session_id = ?"
            cur.execute(query, (session_id,))
            row = cur.fetchone()
            if not row:
                return None
            return UploadSessionModel(
                session_id=str(row["session_id"]),
                created_at=parse_db_datetime(row["created_at"]),
                expires_at=parse_db_datetime(row["expires_at"]),
                last_activity=parse_db_datetime(row["last_activity"]),
                status=row["status"]
            )

    def update_session_activity(self, session_id: str, ttl_minutes: int = 30):
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=ttl_minutes)
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            query = "UPDATE upload_sessions SET last_activity = %s, expires_at = %s WHERE session_id = %s" if self.db.is_postgres else "UPDATE upload_sessions SET last_activity = ?, expires_at = ? WHERE session_id = ?"
            cur.execute(query, (now.isoformat(), expires_at.isoformat(), session_id))
            conn.commit()

    def delete_session(self, session_id: str) -> bool:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            del_tx = "DELETE FROM transactions WHERE session_id = %s" if self.db.is_postgres else "DELETE FROM transactions WHERE session_id = ?"
            cur.execute(del_tx, (session_id,))
            del_sess = "DELETE FROM upload_sessions WHERE session_id = %s" if self.db.is_postgres else "DELETE FROM upload_sessions WHERE session_id = ?"
            cur.execute(del_sess, (session_id,))
            conn.commit()
            return True

    def clean_expired_sessions(self) -> int:
        now = datetime.now(timezone.utc)
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            # Find expired sessions
            find_q = "SELECT session_id FROM upload_sessions WHERE expires_at < %s" if self.db.is_postgres else "SELECT session_id FROM upload_sessions WHERE expires_at < ?"
            cur.execute(find_q, (now if self.db.is_postgres else now.isoformat(),))
            rows = cur.fetchall()
            expired_ids = [str(r["session_id"]) for r in rows]
            if expired_ids:
                for sid in expired_ids:
                    del_tx = "DELETE FROM transactions WHERE session_id = %s" if self.db.is_postgres else "DELETE FROM transactions WHERE session_id = ?"
                    cur.execute(del_tx, (sid,))
                    del_s = "DELETE FROM upload_sessions WHERE session_id = %s" if self.db.is_postgres else "DELETE FROM upload_sessions WHERE session_id = ?"
                    cur.execute(del_s, (sid,))
                conn.commit()
                logger.info(f"Cleaned up {len(expired_ids)} expired session(s).")
            return len(expired_ids)

    def insert_transactions(self, records: List[TransactionModel]) -> int:
        if not records:
            return 0
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            if self.db.is_postgres:
                insert_q = """
                INSERT INTO transactions (session_id, transaction_date, merchant, category, description, amount, type, extra_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = [
                    (
                        r.session_id,
                        r.transaction_date,
                        r.merchant,
                        r.category,
                        r.description,
                        r.amount,
                        r.type,
                        json.dumps(r.extra_data)
                    )
                    for r in records
                ]
                cur.executemany(insert_q, params)
            else:
                insert_q = """
                INSERT INTO transactions (session_id, transaction_date, merchant, category, description, amount, type, extra_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """
                params = [
                    (
                        r.session_id,
                        r.transaction_date.isoformat(),
                        r.merchant,
                        r.category,
                        r.description,
                        r.amount,
                        r.type,
                        json.dumps(r.extra_data)
                    )
                    for r in records
                ]
                cur.executemany(insert_q, params)
            conn.commit()
        return len(records)

    def get_transaction_count(self, session_id: str) -> int:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            q = "SELECT COUNT(*) as cnt FROM transactions WHERE session_id = %s" if self.db.is_postgres else "SELECT COUNT(*) as cnt FROM transactions WHERE session_id = ?"
            cur.execute(q, (session_id,))
            row = cur.fetchone()
            return row["cnt"] if row else 0

    def execute_read_query(self, session_id: str, sql: str, params: Optional[list] = None) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, params or [])
            rows = cur.fetchall()
            results = []
            for r in rows:
                if hasattr(r, "_asdict"):
                    results.append(r._asdict())
                elif isinstance(r, dict):
                    results.append(dict(r))
                else:
                    results.append(dict(r))
            return results


repository = DatabaseRepository()
