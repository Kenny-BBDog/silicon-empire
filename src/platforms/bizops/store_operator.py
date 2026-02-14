"""
业务中台 — Store Operator 店铺运营 (L3)

职责：
- Shopify / Amazon / TikTok 店铺 RPA 操作
- 商品上架/下架/改价
- 订单处理流程
- 店铺数据看板
"""

from __future__ import annotations

from typing import Any

from src.platforms.base_worker import PlatformWorker


class StoreOperatorAgent(PlatformWorker):
    """L3 业务中台 — 店铺运营"""

    ROLE = "l3_store_operator"
    DISPLAY_NAME = "店铺运营 (Store Operator)"
    LLM_ROLE = "coo"    # 用 COO 模型，偏运营
    PLATFORM = "bizops"

    async def create_product_listing(
        self,
        product_data: dict[str, Any],
        platform: str = "shopify",
    ) -> dict[str, Any]:
        """
        在电商平台上架产品。
        需要 L0 审批 (物理层操作 → interrupt_before)。
        """
        await self.initialize()

        await self._memory.think(
            f"准备上架: {product_data.get('title', '?')[:40]} 到 {platform}",
            importance=6,
        )

        # 通过 MCP 调用 Shopify/RPA
        try:
            tools = await self._mcp.get_tools_for_role(self.ROLE)
            create_tools = [t for t in tools if "create_product" in t.name.lower()]
            if create_tools:
                result = await create_tools[0].ainvoke({
                    "action": "create_product",
                    "product_data": product_data,
                })
                return {"status": "created", "platform": platform, "result": result}
        except Exception:
            pass

        # Fallback: 生成上架指令
        prompt = (
            f"生成 {platform} 上架操作指令:\n\n"
            f"## 产品数据\n{product_data}\n\n"
            f"输出 JSON 格式的 API 调用参数。"
        )
        response = await self._llm_think(prompt, {})
        return {"status": "pending_manual", "platform": platform, "instructions": response}

    async def update_pricing(
        self,
        product_id: str,
        new_price: float,
        compare_at_price: float | None = None,
        platform: str = "shopify",
    ) -> dict[str, Any]:
        """改价操作 (需审批)。"""
        await self.initialize()

        await self._memory.think(
            f"改价: {product_id} → ${new_price}",
            importance=5,
        )

        return {
            "action": "update_price",
            "product_id": product_id,
            "new_price": new_price,
            "compare_at_price": compare_at_price,
            "platform": platform,
            "requires_approval": True,
        }

    async def process_orders(
        self, order_status: str = "unfulfilled", platform: str = "shopify"
    ) -> dict[str, Any]:
        """批量处理订单。"""
        await self.initialize()

        prompt = (
            f"查询并处理 {platform} 上状态为 {order_status} 的订单。\n"
            f"生成处理方案: 哪些可以自动发货，哪些需要人工确认。"
        )

        response = await self._llm_think(prompt, {})
        return {"order_status": order_status, "processing_plan": response}
