import httpx
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.core.logging import logger


class MCPClient:
    def __init__(self):
        self.endpoint = settings.POSTGRES_MCP_URL
        self.api_key = settings.MCP_API_KEY
        self.is_connected = False
        self._check_connection()

    def _check_connection(self):
        if self.endpoint:
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
                # Best effort health check
                with httpx.Client(timeout=3.0) as client:
                    resp = client.get(f"{self.endpoint}/tools", headers=headers)
                    if resp.status_code == 200:
                        self.is_connected = True
                        logger.info("Connected to PostgreSQL MCP server.")
            except Exception as e:
                logger.info(f"PostgreSQL MCP server not reachable at {self.endpoint}: {e}. Using direct database driver.")
                self.is_connected = False

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_connected:
            return None
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{self.endpoint}/tools/{tool_name}/invoke",
                    json={"parameters": arguments},
                    headers=headers
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.error(f"Error invoking MCP tool {tool_name}: {e}")
        return None


mcp_client = MCPClient()
