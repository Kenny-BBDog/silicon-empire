"""
Redis MCP Server — Cache and messaging operations as MCP tools.

3 tools: publish_message, read_context, write_context.
全员可用 — Agent 间通信 + 临时思维链存储。
"""

from __future__ import annotations

from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

import json
import os
import redis.asyncio as aioredis

app = Server("redis-server")

_redis = None


async def _get_redis():
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379"),
            decode_responses=True,
        )
    return _redis


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="publish_message",
            description="发布消息到 Redis 频道 (Agent 间通信)",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "频道名 (如 agent_id)"},
                    "message": {"type": "string"},
                    "metadata": {"type": "object"},
                },
                "required": ["channel", "message"],
            },
        ),
        Tool(
            name="read_context",
            description="读取当前会话上下文",
            inputSchema={
                "type": "object",
                "properties": {
                    "trace_id": {"type": "string"},
                    "key": {"type": "string", "description": "上下文 key"},
                },
                "required": ["trace_id", "key"],
            },
        ),
        Tool(
            name="write_context",
            description="写入临时上下文 (带 TTL 自动过期)",
            inputSchema={
                "type": "object",
                "properties": {
                    "trace_id": {"type": "string"},
                    "key": {"type": "string"},
                    "value": {"type": "string"},
                    "ttl_seconds": {"type": "integer", "default": 3600},
                },
                "required": ["trace_id", "key", "value"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        r = await _get_redis()

        if name == "publish_message":
            data = json.dumps({
                "message": arguments["message"],
                "metadata": arguments.get("metadata", {}),
            }, ensure_ascii=False)

            # 用 Redis Streams (与 MessageBus 兼容)
            stream = f"stream:{arguments['channel']}"
            msg_id = await r.xadd(stream, {"data": data})
            return [TextContent(type="text", text=json.dumps({"published": True, "msg_id": msg_id}))]

        elif name == "read_context":
            key = f"ctx:{arguments['trace_id']}:{arguments['key']}"
            value = await r.get(key)
            return [TextContent(type="text", text=value or "null")]

        elif name == "write_context":
            key = f"ctx:{arguments['trace_id']}:{arguments['key']}"
            ttl = arguments.get("ttl_seconds", 3600)
            await r.set(key, arguments["value"], ex=ttl)
            return [TextContent(type="text", text=json.dumps({"written": True, "key": key, "ttl": ttl}))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Redis error: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
