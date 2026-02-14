"""
Shopify MCP Server — E-commerce operations as MCP tools.

4 tools: create_product, update_inventory, get_orders, update_price.
主要被业务中台 (Store Operator) 使用。
所有写操作需要 L0 审批。
"""

from __future__ import annotations

from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

import json
import httpx
import os

app = Server("shopify-server")

# Shopify API Config
SHOPIFY_SHOP = os.environ.get("SHOPIFY_SHOP", "")
SHOPIFY_TOKEN = os.environ.get("SHOPIFY_ADMIN_TOKEN", "")
SHOPIFY_API_VERSION = "2024-01"


def _shopify_url(endpoint: str) -> str:
    return f"https://{SHOPIFY_SHOP}/admin/api/{SHOPIFY_API_VERSION}/{endpoint}.json"


def _headers() -> dict:
    return {"X-Shopify-Access-Token": SHOPIFY_TOKEN, "Content-Type": "application/json"}


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="create_product",
            description="创建 Shopify 商品 (需 L0 审批)",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "body_html": {"type": "string", "description": "产品描述 HTML"},
                    "vendor": {"type": "string"},
                    "product_type": {"type": "string"},
                    "tags": {"type": "string", "description": "逗号分隔的标签"},
                    "variants": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "price": {"type": "string"},
                                "sku": {"type": "string"},
                                "inventory_quantity": {"type": "integer"},
                            },
                        },
                    },
                    "images": {
                        "type": "array",
                        "items": {"type": "object", "properties": {"src": {"type": "string"}}},
                    },
                },
                "required": ["title"],
            },
        ),
        Tool(
            name="update_inventory",
            description="更新库存数量 (需 L0 审批)",
            inputSchema={
                "type": "object",
                "properties": {
                    "inventory_item_id": {"type": "string"},
                    "available": {"type": "integer"},
                    "location_id": {"type": "string"},
                },
                "required": ["inventory_item_id", "available"],
            },
        ),
        Tool(
            name="get_orders",
            description="获取订单列表",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["open", "closed", "cancelled", "any"],
                        "default": "open",
                    },
                    "fulfillment_status": {
                        "type": "string",
                        "enum": ["fulfilled", "unfulfilled", "partial", "any"],
                    },
                    "limit": {"type": "integer", "default": 20},
                },
            },
        ),
        Tool(
            name="update_price",
            description="修改产品价格 (需 L0 审批)",
            inputSchema={
                "type": "object",
                "properties": {
                    "variant_id": {"type": "string"},
                    "price": {"type": "string", "description": "新价格"},
                    "compare_at_price": {"type": "string", "description": "原价 (划线价)"},
                },
                "required": ["variant_id", "price"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Route to Shopify Admin API."""
    if not SHOPIFY_SHOP or not SHOPIFY_TOKEN:
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": "Shopify not configured. Set SHOPIFY_SHOP and SHOPIFY_ADMIN_TOKEN in .env",
            }),
        )]

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if name == "create_product":
                response = await client.post(
                    _shopify_url("products"),
                    headers=_headers(),
                    json={"product": arguments},
                )
                return [TextContent(type="text", text=response.text)]

            elif name == "update_inventory":
                response = await client.post(
                    _shopify_url("inventory_levels/set"),
                    headers=_headers(),
                    json={
                        "inventory_item_id": int(arguments["inventory_item_id"]),
                        "available": arguments["available"],
                        "location_id": int(arguments.get("location_id", "0")),
                    },
                )
                return [TextContent(type="text", text=response.text)]

            elif name == "get_orders":
                params = {
                    "status": arguments.get("status", "open"),
                    "limit": arguments.get("limit", 20),
                }
                if arguments.get("fulfillment_status"):
                    params["fulfillment_status"] = arguments["fulfillment_status"]

                response = await client.get(
                    _shopify_url("orders"),
                    headers=_headers(),
                    params=params,
                )
                return [TextContent(type="text", text=response.text)]

            elif name == "update_price":
                response = await client.put(
                    _shopify_url(f"variants/{arguments['variant_id']}"),
                    headers=_headers(),
                    json={"variant": {
                        "id": int(arguments["variant_id"]),
                        "price": arguments["price"],
                        **({"compare_at_price": arguments["compare_at_price"]}
                           if arguments.get("compare_at_price") else {}),
                    }},
                )
                return [TextContent(type="text", text=response.text)]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=f"Shopify error: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
