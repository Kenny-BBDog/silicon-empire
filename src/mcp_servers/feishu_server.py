"""
Feishu MCP Server — 飞书操作暴露为 MCP 工具

6 tools: send_agent_message, send_approval, send_alert,
         broadcast_meeting, read_channel, reply_message.

所有 L2 Agent 通过此 MCP Server 向飞书发送消息。
"""

from __future__ import annotations

from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

import json

from src.integrations.feishu_client import get_feishu_client

app = Server("feishu-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="send_agent_message",
            description="以指定 Agent 身份在飞书频道发消息",
            inputSchema={
                "type": "object",
                "properties": {
                    "role": {
                        "type": "string",
                        "enum": ["gm", "cgo", "cro", "coo", "cto", "system"],
                        "description": "发言角色",
                    },
                    "channel": {
                        "type": "string",
                        "enum": ["decision", "execution", "alert"],
                        "description": "目标频道",
                    },
                    "content": {"type": "string", "description": "Markdown 正文"},
                    "title": {"type": "string", "description": "卡片标题 (可选)"},
                },
                "required": ["role", "channel", "content"],
            },
        ),
        Tool(
            name="send_approval",
            description="发送审批卡片 (带同意/驳回按钮)",
            inputSchema={
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "enum": ["decision", "alert"]},
                    "title": {"type": "string"},
                    "proposal": {"type": "string", "description": "提案内容"},
                    "trace_id": {"type": "string"},
                },
                "required": ["title", "proposal", "trace_id"],
            },
        ),
        Tool(
            name="send_alert",
            description="发送系统告警到告警频道",
            inputSchema={
                "type": "object",
                "properties": {
                    "level": {"type": "string", "enum": ["critical", "warning", "info"]},
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                },
                "required": ["level", "title", "detail"],
            },
        ),
        Tool(
            name="broadcast_meeting",
            description="广播会议对话 (多 Agent 依次发言)",
            inputSchema={
                "type": "object",
                "properties": {
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"},
                                "title": {"type": "string"},
                            },
                            "required": ["role", "content"],
                        },
                    },
                    "channel": {
                        "type": "string",
                        "enum": ["decision", "execution"],
                        "default": "decision",
                    },
                    "delay": {
                        "type": "number",
                        "default": 1.0,
                        "description": "每条消息间隔秒数",
                    },
                },
                "required": ["messages"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    feishu = get_feishu_client()

    try:
        if name == "send_agent_message":
            result = await feishu.send_as(
                role=arguments["role"],
                channel=arguments["channel"],
                content=arguments["content"],
                title=arguments.get("title", ""),
            )
            return [TextContent(type="text", text=json.dumps(result, default=str))]

        elif name == "send_approval":
            result = await feishu.send_approval(
                channel=arguments.get("channel", "decision"),
                title=arguments["title"],
                proposal=arguments["proposal"],
                trace_id=arguments["trace_id"],
            )
            return [TextContent(type="text", text=json.dumps(result, default=str))]

        elif name == "send_alert":
            result = await feishu.send_alert(
                level=arguments["level"],
                title=arguments["title"],
                detail=arguments["detail"],
            )
            return [TextContent(type="text", text=json.dumps(result, default=str))]

        elif name == "broadcast_meeting":
            results = await feishu.broadcast_meeting(
                messages=arguments["messages"],
                channel=arguments.get("channel", "decision"),
                delay=arguments.get("delay", 1.0),
            )
            return [TextContent(type="text", text=json.dumps(results, default=str))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Feishu error: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
