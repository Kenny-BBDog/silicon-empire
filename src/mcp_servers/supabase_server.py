"""
Database MCP Server — PostgreSQL 本地版 (替代 Supabase).

提供 12 个工具，覆盖所有 6 张表的 CRUD + 向量搜索。
通过 MCP 协议暴露，各 Agent 按权限矩阵调用。
直连本地 PostgreSQL + pgvector，零网络延迟。
"""

from __future__ import annotations

from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

import psycopg
from psycopg.rows import dict_row

import json
import os

app = Server("database-server")

# ─── PostgreSQL Client ───

_conn = None


def _get_conn():
    global _conn
    if _conn is None:
        db_url = os.environ.get(
            "DATABASE_URL",
            "postgresql://silicon:silicon2026@localhost:5432/silicon_empire",
        )
        _conn = psycopg.connect(db_url, row_factory=dict_row, autocommit=True)
    return _conn


def _query(sql: str, params: list | tuple = ()) -> list[dict]:
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def _execute(sql: str, params: list | tuple = ()) -> list[dict]:
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        if cur.description:
            return [dict(r) for r in cur.fetchall()]
        return []


# ─── Tool Definitions ───

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        # Products
        Tool(
            name="query_products",
            description="按条件查询产品库 (category, platform, limit)",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "产品品类"},
                    "platform": {"type": "string", "description": "来源平台"},
                    "limit": {"type": "integer", "default": 20},
                },
            },
        ),
        Tool(
            name="search_products_vector",
            description="语义搜索产品 (pgvector 向量检索)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                    "top_k": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="insert_product",
            description="写入新产品到产品库",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "category": {"type": "string"},
                    "source_platform": {"type": "string"},
                    "price_range": {"type": "object"},
                    "selling_points": {"type": "array", "items": {"type": "string"}},
                    "risk_flags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["title"],
            },
        ),
        # Suppliers
        Tool(
            name="query_suppliers",
            description="查询供应商库",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        ),
        # Policies
        Tool(
            name="search_policies_vector",
            description="语义搜索合规政策 (CRO 风控引用)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "政策检索词"},
                    "top_k": {"type": "integer", "default": 10},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="query_policies",
            description="按平台/类别查询合规规则",
            inputSchema={
                "type": "object",
                "properties": {
                    "platform": {"type": "string"},
                    "category": {"type": "string"},
                    "severity": {"type": "string", "enum": ["BAN", "WARNING", "INFO"]},
                },
            },
        ),
        # Decisions
        Tool(
            name="read_decisions",
            description="查询历史决策记录",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {"type": "string", "enum": ["EXPLORATION", "EXECUTION"]},
                    "verdict": {"type": "string"},
                    "limit": {"type": "integer", "default": 10},
                },
            },
        ),
        Tool(
            name="write_decision",
            description="写入决策记录 (GM 专用)",
            inputSchema={
                "type": "object",
                "properties": {
                    "trace_id": {"type": "string"},
                    "mode": {"type": "string"},
                    "meeting_type": {"type": "string"},
                    "proposal_summary": {"type": "string"},
                    "l0_verdict": {"type": "string"},
                    "decision_matrix": {"type": "object"},
                    "meeting_transcript": {"type": "object"},
                },
                "required": ["trace_id", "proposal_summary"],
            },
        ),
        # Tool Registry
        Tool(
            name="read_tool_registry",
            description="查询工具注册表 (CTO 专用)",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["ACTIVE", "DEPRECATED", "BROKEN"]},
                },
            },
        ),
        Tool(
            name="update_tool_registry",
            description="更新工具注册信息 (CTO 专用)",
            inputSchema={
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string"},
                    "status": {"type": "string"},
                    "version": {"type": "integer"},
                    "last_error_log": {"type": "string"},
                },
                "required": ["tool_name"],
            },
        ),
        # Interactions
        Tool(
            name="log_interaction",
            description="记录 CRM 交互 (关系中台)",
            inputSchema={
                "type": "object",
                "properties": {
                    "contact_type": {"type": "string"},
                    "contact_name": {"type": "string"},
                    "channel": {"type": "string"},
                    "direction": {"type": "string"},
                    "summary": {"type": "string"},
                    "raw_content": {"type": "string"},
                },
                "required": ["contact_name", "summary"],
            },
        ),
        # Search Interactions
        Tool(
            name="search_interactions_vector",
            description="语义搜索 CRM 交互记录",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "top_k": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
        ),
    ]


# ─── Tool Handlers ───

@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        if name == "query_products":
            sql = "SELECT * FROM products WHERE 1=1"
            params: list = []
            if arguments.get("category"):
                sql += " AND category = %s"
                params.append(arguments["category"])
            if arguments.get("platform"):
                sql += " AND source_platform = %s"
                params.append(arguments["platform"])
            sql += " ORDER BY created_at DESC LIMIT %s"
            params.append(arguments.get("limit", 20))
            rows = _query(sql, params)
            return [TextContent(type="text", text=json.dumps(rows, default=str))]

        elif name == "search_products_vector":
            from src.platforms.data_intel.rag_pipeline import get_rag
            rag = await get_rag()
            results = await rag.search_products(arguments["query"], arguments.get("top_k", 5))
            return [TextContent(type="text", text=json.dumps(results, default=str))]

        elif name == "insert_product":
            cols = ", ".join(arguments.keys())
            placeholders = ", ".join(["%s"] * len(arguments))
            vals = [
                json.dumps(v) if isinstance(v, (dict, list)) else v
                for v in arguments.values()
            ]
            rows = _execute(
                f"INSERT INTO products ({cols}) VALUES ({placeholders}) RETURNING *",
                vals,
            )
            return [TextContent(type="text", text=json.dumps(rows, default=str))]

        elif name == "query_suppliers":
            sql = "SELECT * FROM suppliers WHERE 1=1"
            params = []
            if arguments.get("category"):
                sql += " AND %s = ANY(products)"
                params.append(arguments["category"])
            sql += " ORDER BY created_at DESC LIMIT %s"
            params.append(arguments.get("limit", 10))
            rows = _query(sql, params)
            return [TextContent(type="text", text=json.dumps(rows, default=str))]

        elif name == "search_policies_vector":
            from src.platforms.data_intel.rag_pipeline import get_rag
            rag = await get_rag()
            results = await rag.search_policies(arguments["query"], arguments.get("top_k", 10))
            return [TextContent(type="text", text=json.dumps(results, default=str))]

        elif name == "query_policies":
            sql = "SELECT * FROM platform_policies WHERE 1=1"
            params = []
            if arguments.get("platform"):
                sql += " AND platform = %s"
                params.append(arguments["platform"])
            if arguments.get("category"):
                sql += " AND category = %s"
                params.append(arguments["category"])
            if arguments.get("severity"):
                sql += " AND severity = %s"
                params.append(arguments["severity"])
            rows = _query(sql, params)
            return [TextContent(type="text", text=json.dumps(rows, default=str))]

        elif name == "read_decisions":
            sql = "SELECT * FROM strategic_decisions WHERE 1=1"
            params = []
            if arguments.get("mode"):
                sql += " AND mode = %s"
                params.append(arguments["mode"])
            if arguments.get("verdict"):
                sql += " AND l0_verdict = %s"
                params.append(arguments["verdict"])
            sql += " ORDER BY created_at DESC LIMIT %s"
            params.append(arguments.get("limit", 10))
            rows = _query(sql, params)
            return [TextContent(type="text", text=json.dumps(rows, default=str))]

        elif name == "write_decision":
            cols = ", ".join(arguments.keys())
            placeholders = ", ".join(["%s"] * len(arguments))
            vals = [
                json.dumps(v) if isinstance(v, (dict, list)) else v
                for v in arguments.values()
            ]
            rows = _execute(
                f"INSERT INTO strategic_decisions ({cols}) VALUES ({placeholders}) RETURNING *",
                vals,
            )
            return [TextContent(type="text", text=json.dumps(rows, default=str))]

        elif name == "read_tool_registry":
            sql = "SELECT * FROM tool_registry WHERE 1=1"
            params = []
            if arguments.get("status"):
                sql += " AND status = %s"
                params.append(arguments["status"])
            rows = _query(sql, params)
            return [TextContent(type="text", text=json.dumps(rows, default=str))]

        elif name == "update_tool_registry":
            tool_name = arguments.pop("tool_name")
            set_parts = []
            params = []
            for col, val in arguments.items():
                set_parts.append(f"{col} = %s")
                params.append(val)
            params.append(tool_name)
            rows = _execute(
                f"UPDATE tool_registry SET {', '.join(set_parts)} WHERE tool_name = %s RETURNING *",
                params,
            )
            return [TextContent(type="text", text=json.dumps(rows, default=str))]

        elif name == "log_interaction":
            cols = ", ".join(arguments.keys())
            placeholders = ", ".join(["%s"] * len(arguments))
            vals = list(arguments.values())
            rows = _execute(
                f"INSERT INTO interactions ({cols}) VALUES ({placeholders}) RETURNING *",
                vals,
            )
            return [TextContent(type="text", text=json.dumps(rows, default=str))]

        elif name == "search_interactions_vector":
            from src.platforms.data_intel.rag_pipeline import get_rag
            rag = await get_rag()
            results = await rag.search_interactions(arguments["query"], arguments.get("top_k", 5))
            return [TextContent(type="text", text=json.dumps(results, default=str))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# ─── Entry Point ───

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
