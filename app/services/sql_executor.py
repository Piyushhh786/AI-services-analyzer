from typing import List, Dict, Any, Tuple
from app.database.repository import repository
from app.services.sql_validator import SQLValidator
from app.core.exceptions import SQLSecurityException
from app.core.logging import logger


class SQLExecutor:
    @staticmethod
    def execute(session_id: str, sql: str) -> Tuple[List[Dict[str, Any]], str]:
        """
        Validates and executes SQL scoped to session_id.
        Returns (rows, error_message).
        """
        is_valid, safe_sql, error = SQLValidator.validate_and_sanitize(sql, session_id)
        if not is_valid:
            logger.warning(f"SQL validation failed: {error}")
            return [], error

        # Append LIMIT if not present
        if "LIMIT" not in safe_sql.upper():
            safe_sql = f"{safe_sql} LIMIT 100"

        try:
            results = repository.execute_read_query(session_id, safe_sql)
            return results, ""
        except Exception as e:
            logger.error(f"Error executing SQL: {e}")
            return [], str(e)
