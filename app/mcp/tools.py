from typing import List, Dict, Any, Optional
from app.mcp.client import mcp_client
from app.services.sql_executor import SQLExecutor
from app.core.logging import logger


class DatabaseTools:
    @staticmethod
    def query_database(session_id: str, sql: str) -> List[Dict[str, Any]]:
        """
        Executes a read-only query using either MCP server if available,
        or the native validated SQLExecutor.
        """
        if mcp_client.is_connected:
            mcp_res = mcp_client.execute_tool("execute_query", {"query": sql, "session_id": session_id})
            if mcp_res and "result" in mcp_res:
                return mcp_res["result"]

        # Default native executor
        rows, error = SQLExecutor.execute(session_id, sql)
        if error:
            raise RuntimeError(f"Database execution failed: {error}")
        return rows
