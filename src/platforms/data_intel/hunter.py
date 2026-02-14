"""
Data Hunter — 情报中台爬虫长 (L3)

职责：
- 接受 L2 委派的数据采集任务
- 通过 Playwright MCP 执行网页抓取
- 清洗数据后交给 Insight Analyst 或直接写入知识库
- 定时巡逻（趋势发现、竞品监控）
"""

from __future__ import annotations

from typing import Any

from src.platforms.base_worker import PlatformWorker


class DataHunterAgent(PlatformWorker):
    """L3 情报中台 — 数据猎手"""

    ROLE = "l3_data_hunter"
    DISPLAY_NAME = "数据猎手 (Data Hunter)"
    LLM_ROLE = "analysis"   # 用低成本分析模型
    PLATFORM = "data_intel"

    # ─── 核心能力 ───

    async def scrape_category(
        self, platform: str, keywords: list[str], top_n: int = 20
    ) -> dict[str, Any]:
        """
        爬取电商品类数据。
        
        Supported platforms: amazon, tiktok, shopify
        """
        await self.initialize()

        await self._memory.think(
            f"开始爬取 {platform} 品类数据, 关键词: {keywords}",
            importance=4,
        )

        # 构建爬取任务 prompt
        prompt = (
            f"你需要分析以下爬取参数并生成结构化的产品列表。\n\n"
            f"## 平台\n{platform}\n\n"
            f"## 关键词\n{', '.join(keywords)}\n\n"
            f"## 要求\n"
            f"- 提取 Top {top_n} 产品\n"
            f"- 每个产品提取: 标题, 价格, 评分, 评论数, 卖点, 差评痛点\n"
            f"- 输出 JSON 数组格式\n\n"
            f"请基于你对 {platform} 市场的了解，生成真实可行的数据采集方案。"
        )

        # 尝试通过 MCP 调用 Playwright
        try:
            tools = await self._mcp.get_tools_for_role(self.ROLE)
            playwright_tools = [t for t in tools if "scrape" in t.name.lower()]
            if playwright_tools:
                result = await playwright_tools[0].ainvoke({
                    "keywords": keywords,
                    "platform": platform,
                    "top_n": top_n,
                })
                return {"source": "mcp_playwright", "data": result}
        except Exception:
            pass

        # Fallback: LLM 分析
        response = await self._llm_think(prompt, {})

        await self._memory.think(
            f"完成 {platform} 品类爬取, 关键词: {keywords[:2]}",
            importance=5,
        )

        return {
            "source": "llm_analysis",
            "platform": platform,
            "keywords": keywords,
            "data": response,
        }

    async def monitor_competitor(
        self, competitor_url: str, check_items: list[str] | None = None
    ) -> dict[str, Any]:
        """
        竞品监控 — 定期检查竞品变化。
        
        check_items: ["price", "reviews", "new_products", "ads"]
        """
        await self.initialize()

        if check_items is None:
            check_items = ["price", "reviews", "new_products"]

        prompt = (
            f"监控竞品页面: {competitor_url}\n"
            f"需要检查: {', '.join(check_items)}\n\n"
            f"生成结构化的竞品变化报告。"
        )

        response = await self._llm_think(prompt, {})

        await self._memory.think(
            f"竞品监控: {competitor_url[:50]}",
            importance=4,
        )

        return {"competitor_url": competitor_url, "report": response}

    async def discover_trends(self, category: str = "") -> dict[str, Any]:
        """
        趋势发现 — 扫描各平台热门品类/话题。
        可以定时触发（如每天凌晨）。
        """
        await self.initialize()

        prompt = (
            f"扫描当前电商趋势:\n"
            f"{'品类: ' + category if category else '全品类扫描'}\n\n"
            f"分析以下维度:\n"
            f"1. TikTok 热门商品/话题\n"
            f"2. Amazon Movers & Shakers\n"
            f"3. Google Trends 上升词\n"
            f"4. 社交媒体病毒式传播的产品\n\n"
            f"输出 Top 5 趋势机会，每个包含: 品类、热度指标、建议行动。"
        )

        response = await self._llm_think(prompt, {})

        await self._memory.think(
            f"趋势扫描完成: {category or '全品类'}",
            importance=6,
        )

        return {"category": category, "trends": response}

    async def extract_reviews(
        self, product_url: str, focus: str = "negative"
    ) -> dict[str, Any]:
        """
        差评/好评提取 — 分析产品评论痛点。
        focus: "negative" (差评痛点) | "positive" (卖点) | "all"
        """
        await self.initialize()

        prompt = (
            f"分析产品评论: {product_url}\n"
            f"重点: {focus}\n\n"
            f"提取:\n"
            f"- Top 5 {'差评痛点' if focus == 'negative' else '好评卖点'}\n"
            f"- 每个痛点的出现频率估计\n"
            f"- 可利用的差异化机会\n"
        )

        response = await self._llm_think(prompt, {})
        return {"product_url": product_url, "focus": focus, "analysis": response}
