"""
关系中台 — Customer Success 客户成功 (L3)

职责：
- 客户评价监控与回复
- 售后问题处理
- 客户情绪分析
- 复购/留存策略
"""

from __future__ import annotations

from typing import Any

from src.platforms.base_worker import PlatformWorker
from src.platforms.data_intel.rag_pipeline import get_rag


class CustomerSuccessAgent(PlatformWorker):
    """L3 关系中台 — 客户成功"""

    ROLE = "l3_customer_success"
    DISPLAY_NAME = "客户成功 (Customer Success)"
    LLM_ROLE = "creative"   # 需要有温度的回复
    PLATFORM = "relationship"

    async def respond_to_review(
        self,
        review: dict[str, Any],
        product_info: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        生成评论回复。
        
        review 示例:
        {
            "rating": 3,
            "text": "Product is okay but arrived damaged",
            "reviewer": "John D.",
            "platform": "amazon",
        }
        """
        await self.initialize()

        rating = review.get("rating", 3)
        sentiment = "差评" if rating <= 2 else "中评" if rating == 3 else "好评"

        prompt = (
            f"回复客户 {sentiment}:\n\n"
            f"## 评论\n"
            f"- 评分: {rating}/5\n"
            f"- 内容: {review.get('text', '')}\n"
            f"- 平台: {review.get('platform', 'amazon')}\n\n"
            f"{'## 产品信息\\n' + str(product_info) if product_info else ''}\n\n"
            f"## 回复原则\n"
            f"1. 感谢客户反馈\n"
            f"2. 对问题表示歉意 (如有)\n"
            f"3. 提供解决方案 (退换/补发/折扣码)\n"
            f"4. 不要暴露是 AI 写的\n"
            f"5. 语气: 真诚、专业、有温度\n"
            f"6. 长度: 3-5 句\n"
        )

        response = await self._llm_think(prompt, {})

        # 记录交互
        rag = await get_rag()
        await rag.ingest_interaction({
            "contact_type": "CUSTOMER",
            "contact_name": review.get("reviewer", "Anonymous"),
            "channel": review.get("platform", "amazon"),
            "direction": "outbound",
            "summary": f"回复 {sentiment}: {review.get('text', '')[:80]}",
        })

        return {"reply": response, "sentiment": sentiment, "requires_approval": True}

    async def analyze_reviews_batch(
        self, reviews: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """批量分析评论，提取洞察。"""
        await self.initialize()

        prompt = (
            f"分析以下 {len(reviews)} 条评论:\n\n"
            f"## 评论\n{reviews[:20]}\n\n"  # 最多分析 20 条
            f"## 输出\n"
            f"1. **情绪分布** (正面/中性/负面 占比)\n"
            f"2. **差评 Top 5 主题** (附频率)\n"
            f"3. **好评 Top 5 主题** (附频率)\n"
            f"4. **紧急问题** (需立即处理)\n"
            f"5. **产品改进建议**\n"
            f"6. **竞品对比提及**\n"
        )

        response = await self._llm_think(prompt, {})

        await self._memory.think(
            f"分析了 {len(reviews)} 条评论，发现关键洞察",
            importance=6,
        )

        return {"analysis": response, "review_count": len(reviews)}

    async def draft_follow_up(
        self, customer_info: dict[str, Any], purpose: str = "retention"
    ) -> dict[str, Any]:
        """
        起草客户跟进邮件。
        purpose: "retention" | "upsell" | "feedback" | "win_back"
        """
        await self.initialize()

        prompt = (
            f"起草客户跟进邮件:\n\n"
            f"## 客户\n{customer_info}\n\n"
            f"## 目的: {purpose}\n\n"
            f"## 要求\n"
            f"- 个性化 (提及客户购买的产品)\n"
            f"- 附带优惠/激励 (如适用)\n"
            f"- 不要太推销\n"
            f"- 提供退订选项\n"
        )

        response = await self._llm_think(prompt, {})
        return {"email_draft": response, "purpose": purpose, "requires_approval": True}
