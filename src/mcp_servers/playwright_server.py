"""
Playwright MCP Server — Browser automation as MCP tools.

提供 5 个工具：品类爬取、TikTok 热门、侵权检测、Shopify RPA、网页截图。
通过 Playwright FastAPI 微服务执行实际的浏览器操作。
"""

from __future__ import annotations

from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

import json
import httpx
import os

app = Server("playwright-server")

# RPA API base URL (Docker compose 中的 rpa-api 服务)
RPA_BASE_URL = os.environ.get("RPA_API_URL", "http://localhost:8001")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="scrape_amazon_category",
            description="爬取 Amazon 品类 Top N 产品 (标题/价格/评分/评论数)",
            inputSchema={
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "array", "items": {"type": "string"},
                        "description": "搜索关键词列表",
                    },
                    "platform": {"type": "string", "default": "amazon"},
                    "top_n": {"type": "integer", "default": 20},
                    "market": {"type": "string", "default": "US"},
                },
                "required": ["keywords"],
            },
        ),
        Tool(
            name="scrape_tiktok_trending",
            description="爬取 TikTok Shop 热门商品",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "品类"},
                    "region": {"type": "string", "default": "US"},
                    "top_n": {"type": "integer", "default": 20},
                },
            },
        ),
        Tool(
            name="check_image_originality",
            description="图片反向搜索检测侵权 (Google Images / TinEye)",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_url": {"type": "string", "description": "图片 URL"},
                    "check_sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": ["google_images", "tineye"],
                    },
                },
                "required": ["image_url"],
            },
        ),
        Tool(
            name="operate_shopify_admin",
            description="Shopify 后台 RPA 操作 (上架/改价/改库存)",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["create_product", "update_price", "update_inventory"],
                    },
                    "product_data": {"type": "object", "description": "产品数据"},
                },
                "required": ["action", "product_data"],
            },
        ),
        Tool(
            name="screenshot_page",
            description="截取网页截图 (取证/监控)",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "目标 URL"},
                    "full_page": {"type": "boolean", "default": False},
                    "selector": {"type": "string", "description": "可选的 CSS 选择器"},
                },
                "required": ["url"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Route tool calls to the Playwright RPA API microservice."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{RPA_BASE_URL}/api/{name}",
                json=arguments,
            )

            if response.status_code == 200:
                data = response.json()
                return [TextContent(type="text", text=json.dumps(data, default=str, ensure_ascii=False))]
            else:
                return [TextContent(
                    type="text",
                    text=f"RPA API error ({response.status_code}): {response.text[:500]}",
                )]

    except httpx.ConnectError:
        return [TextContent(
            type="text",
            text=f"RPA API unavailable at {RPA_BASE_URL}. Is docker-compose running?",
        )]
    except Exception as e:
        return [TextContent(type="text", text=f"Playwright error: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
