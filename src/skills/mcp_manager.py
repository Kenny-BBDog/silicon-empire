"""
MCP Client Manager.

Wraps langchain-mcp-adapters to provide role-aware MCP tool access.
Each agent gets only the MCP servers it has permission for.
"""

from __future__ import annotations

from typing import Any

from src.core.guards import MCP_PERMISSIONS


class MCPManager:
    """
    Manages MCP server connections and provides role-filtered tool access.
    
    Uses langchain-mcp-adapters for LangGraph-native MCP tool consumption.
    """

    # MCP server definitions — command to launch each server
    SERVER_CONFIGS: dict[str, dict[str, Any]] = {
        "supabase": {
            "command": "python",
            "args": ["src/mcp_servers/supabase_server.py"],
            "transport": "stdio",
        },
        "playwright": {
            "command": "python",
            "args": ["src/mcp_servers/playwright_server.py"],
            "transport": "stdio",
        },
        "gmail": {
            "command": "python",
            "args": ["src/mcp_servers/gmail_server.py"],
            "transport": "stdio",
        },
        "redis": {
            "command": "python",
            "args": ["src/mcp_servers/redis_server.py"],
            "transport": "stdio",
        },
        "filesystem": {
            "command": "python",
            "args": ["src/mcp_servers/filesystem_server.py"],
            "transport": "stdio",
        },
        "shopify": {
            "command": "python",
            "args": ["src/mcp_servers/shopify_server.py"],
            "transport": "stdio",
        },
        "feishu": {
            "command": "python",
            "args": ["src/mcp_servers/feishu_server.py"],
            "transport": "stdio",
        },
    }

    def __init__(self) -> None:
        self._client = None
        self._tools: list[Any] = []

    async def connect(self, role: str) -> list[Any]:
        """
        Connect to MCP servers permitted for the given role.
        Returns a list of LangGraph-compatible tools.
        
        Args:
            role: Agent role (gm, cgo, coo, cro, cto).
        
        Returns:
            List of tools from permitted MCP servers.
        """
        try:
            from langchain_mcp_adapters.client import MultiServerMCPClient
        except ImportError:
            print("Warning: langchain-mcp-adapters not installed. MCP tools unavailable.")
            return []

        # Filter servers by role permissions
        permitted_servers = {}
        role_perms = MCP_PERMISSIONS.get(role, {})

        for server_name in role_perms:
            if server_name in self.SERVER_CONFIGS:
                permitted_servers[server_name] = self.SERVER_CONFIGS[server_name]

        if not permitted_servers:
            return []

        try:
            self._client = MultiServerMCPClient(permitted_servers)
            await self._client.__aenter__()
            self._tools = self._client.get_tools()
            return self._tools
        except Exception as e:
            print(f"Warning: MCP connection failed for role {role}: {e}")
            return []

    async def disconnect(self) -> None:
        """Disconnect from all MCP servers."""
        if self._client:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception:
                pass
            self._client = None
            self._tools = []

    def get_tools(self) -> list[Any]:
        """Get currently connected tools."""
        return self._tools

    def get_tool_names(self) -> list[str]:
        """Get names of all available tools."""
        return [t.name for t in self._tools]

    @staticmethod
    def get_permitted_servers(role: str) -> list[str]:
        """Get list of MCP servers a role has access to."""
        return list(MCP_PERMISSIONS.get(role, {}).keys())

    @staticmethod
    def get_role_permissions(role: str) -> dict[str, str]:
        """Get detailed permissions for a role."""
        return MCP_PERMISSIONS.get(role, {})
