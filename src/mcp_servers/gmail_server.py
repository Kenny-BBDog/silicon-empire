"""
Gmail MCP Server — Email read/write as MCP tools.

4 tools: send_email, read_inbox, parse_attachment, search_emails.
主要被关系中台 (Sourcing Liaison, Customer Success) 使用。
发送邮件需要 L0 审批 (物理层操作)。
"""

from __future__ import annotations

from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

import json
import os

app = Server("gmail-server")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="send_email",
            description="发送邮件 (需 L0 审批)",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "收件人"},
                    "subject": {"type": "string"},
                    "body": {"type": "string", "description": "邮件正文 (支持 HTML)"},
                    "cc": {"type": "string"},
                    "attachments": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "附件路径列表",
                    },
                },
                "required": ["to", "subject", "body"],
            },
        ),
        Tool(
            name="read_inbox",
            description="读取收件箱最新邮件",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_results": {"type": "integer", "default": 10},
                    "label": {"type": "string", "default": "INBOX"},
                    "unread_only": {"type": "boolean", "default": True},
                },
            },
        ),
        Tool(
            name="search_emails",
            description="搜索历史邮件",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Gmail 搜索查询"},
                    "max_results": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="parse_attachment",
            description="解析邮件附件 (PDF/Excel/CSV)",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string"},
                    "attachment_id": {"type": "string"},
                    "file_type": {
                        "type": "string",
                        "enum": ["pdf", "xlsx", "csv"],
                    },
                },
                "required": ["message_id", "attachment_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """
    Gmail API integration.
    Uses Google Gmail API via service account or OAuth2.
    """
    try:
        # NOTE: 实际实现需要 google-auth + googleapiclient
        # 这里用占位逻辑，真实部署时替换

        if name == "send_email":
            # 物理层操作 — 需要在 LangGraph 中 interrupt_before
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "queued",
                    "to": arguments["to"],
                    "subject": arguments["subject"],
                    "requires_approval": True,
                    "message": "Email queued for L0 approval",
                }),
            )]

        elif name == "read_inbox":
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "ok",
                    "message": "Gmail API not yet connected. Configure OAuth2 in .env",
                    "emails": [],
                }),
            )]

        elif name == "search_emails":
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "ok",
                    "query": arguments["query"],
                    "results": [],
                }),
            )]

        elif name == "parse_attachment":
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "ok",
                    "message_id": arguments["message_id"],
                    "parsed_content": "Attachment parsing not yet implemented",
                }),
            )]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Gmail error: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
