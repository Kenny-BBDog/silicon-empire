"""
Filesystem MCP Server — File operations as MCP tools.

3 tools: read_file, write_file, list_directory.
CTO 和 AutoLab 专用 — 代码修复时需要读写文件。
"""

from __future__ import annotations

from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

import json
import os
from pathlib import Path

app = Server("filesystem-server")

# Sandbox root — 限制文件操作在项目目录内
ALLOWED_ROOT = os.environ.get("PROJECT_ROOT", os.getcwd())


def _safe_path(path: str) -> str | None:
    """Ensure the path is within the allowed root."""
    resolved = os.path.realpath(path)
    if resolved.startswith(os.path.realpath(ALLOWED_ROOT)):
        return resolved
    return None


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="read_file",
            description="读取代码/配置文件内容",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件相对路径"},
                    "encoding": {"type": "string", "default": "utf-8"},
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="write_file",
            description="写入文件 (仅限沙盒目录)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件相对路径"},
                    "content": {"type": "string", "description": "文件内容"},
                    "encoding": {"type": "string", "default": "utf-8"},
                },
                "required": ["path", "content"],
            },
        ),
        Tool(
            name="list_directory",
            description="列出目录内容",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "目录路径", "default": "."},
                    "recursive": {"type": "boolean", "default": False},
                    "pattern": {"type": "string", "description": "通配符筛选 (如 *.py)"},
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        if name == "read_file":
            path = _safe_path(os.path.join(ALLOWED_ROOT, arguments["path"]))
            if not path:
                return [TextContent(type="text", text="Error: Path outside allowed directory")]
            if not os.path.isfile(path):
                return [TextContent(type="text", text=f"Error: File not found: {path}")]

            with open(path, "r", encoding=arguments.get("encoding", "utf-8")) as f:
                content = f.read()

            return [TextContent(type="text", text=content[:50000])]  # 限制 50KB

        elif name == "write_file":
            path = _safe_path(os.path.join(ALLOWED_ROOT, arguments["path"]))
            if not path:
                return [TextContent(type="text", text="Error: Path outside allowed directory")]

            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding=arguments.get("encoding", "utf-8")) as f:
                f.write(arguments["content"])

            return [TextContent(type="text", text=json.dumps({"written": path, "bytes": len(arguments["content"])}))]

        elif name == "list_directory":
            dir_path = _safe_path(os.path.join(ALLOWED_ROOT, arguments.get("path", ".")))
            if not dir_path:
                return [TextContent(type="text", text="Error: Path outside allowed directory")]

            p = Path(dir_path)
            pattern = arguments.get("pattern", "*")

            if arguments.get("recursive"):
                files = [str(f.relative_to(p)) for f in p.rglob(pattern) if f.is_file()]
            else:
                files = [str(f.relative_to(p)) for f in p.glob(pattern)]

            return [TextContent(type="text", text=json.dumps(files[:200]))]  # 限制 200 条

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Filesystem error: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
