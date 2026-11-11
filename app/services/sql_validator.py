import re
from typing import Tuple, List
from app.core.logging import logger

try:
    import sqlglot
    from sqlglot import exp
    SQLGLOT_AVAILABLE = True
except ImportError:
    SQLGLOT_AVAILABLE = False

ALLOWED_TABLES = {"transactions", "upload_sessions"}

FORBIDDEN_KEYWORDS = [
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE",
    "GRANT", "REVOKE", "ATTACH", "DETACH", "PRAGMA", "EXEC", "EXECUTE",
    "XP_", "SP_", "PG_SLEEP", "BENCHMARK", "INTO OUTFILE", "LOAD_FILE"
]


class SQLValidator:
    @staticmethod
    def validate_and_sanitize(sql: str, session_id: str) -> Tuple[bool, str, str]:
        """
        Validates the generated SQL using SQLGlot (or fallback parser) and ensures session scoping.
        Returns (is_valid, sanitized_sql, error_message).
        """
        raw_sql = sql.strip().rstrip(";")
        
        # 1. Quick forbidden keywords check
        upper_sql = raw_sql.upper()
        for kw in FORBIDDEN_KEYWORDS:
            if re.search(r"\b" + re.escape(kw) + r"\b", upper_sql):
                return False, "", f"Forbidden SQL operation detected: {kw}"

        # 2. Must start with SELECT
        if not upper_sql.startswith("SELECT"):
            return False, "", "Only SELECT statements are permitted."

        # 3. Use SQLGlot if available
        if SQLGLOT_AVAILABLE:
            try:
                expression = sqlglot.parse_one(raw_sql)
                if not isinstance(expression, exp.Select):
                    return False, "", "Only SELECT statements are permitted."

                tables = [t.name.lower() for t in expression.find_all(exp.Table)]
                for table in tables:
                    if table and table not in ALLOWED_TABLES:
                        return False, "", f"Access to table '{table}' is not permitted."

                where_clause = expression.find(exp.Where)
                session_condition = f"session_id = '{session_id}'"
                
                if not where_clause:
                    sanitized_sql = f"{expression.sql()} WHERE {session_condition}"
                else:
                    where_sql = where_clause.sql()
                    if session_id not in where_sql and "session_id" not in where_sql.lower():
                        sanitized_sql = f"{expression.sql()} AND {session_condition}"
                    else:
                        sanitized_sql = expression.sql()

                return True, sanitized_sql, ""
            except Exception as e:
                logger.warning(f"SQLGlot parse error: {e}. Falling back to rule-based sanitizer.")

        # 4. Fallback sanitizer
        session_condition = f"session_id = '{session_id}'"
        if "WHERE" not in upper_sql:
            # Check for GROUP BY / ORDER BY / LIMIT
            match = re.search(r"\b(GROUP\s+BY|ORDER\s+BY|LIMIT)\b", raw_sql, re.IGNORECASE)
            if match:
                idx = match.start()
                sanitized_sql = f"{raw_sql[:idx].strip()} WHERE {session_condition} {raw_sql[idx:].strip()}"
            else:
                sanitized_sql = f"{raw_sql} WHERE {session_condition}"
        else:
            if session_id not in raw_sql and "session_id" not in raw_sql.lower():
                # Inject session condition after WHERE
                sanitized_sql = re.sub(r"\bWHERE\b", f"WHERE {session_condition} AND ", raw_sql, count=1, flags=re.IGNORECASE)
            else:
                sanitized_sql = raw_sql

        return True, sanitized_sql, ""
