"""
Insight Analyst — 情报中台分析师 (L3)

职责：
- 对 Hunter 采集的原始数据进行深度分析
- 利用 RAG 检索历史数据做交叉验证
- 生成结构化的洞察报告
- 为 L2 决策层提供数据支撑
"""

from __future__ import annotations

from typing import Any

from src.platforms.base_worker import PlatformWorker
from src.platforms.data_intel.rag_pipeline import get_rag


class InsightAnalystAgent(PlatformWorker):
    """L3 情报中台 — 洞察分析师"""

    ROLE = "l3_insight_analyst"
    DISPLAY_NAME = "洞察分析师 (Insight Analyst)"
    LLM_ROLE = "analysis"   # 低成本分析模型，处理大量数据
    PLATFORM = "data_intel"

    # ─── 核心能力 ───

    async def analyze_market(
        self, category: str, raw_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        市场分析 — 从原始数据中提取市场洞察。
        
        通常被 CGO 的 product_research Skill 调用，
        或者 Hunter 爬取后交给 Analyst 处理。
        """
        await self.initialize()
        rag = await get_rag()

        # RAG: 检索历史相关数据
        historical_context = await rag.build_rag_context(
            query=category,
            sources=["products"],
            top_k=5,
        )

        prompt = (
            f"你是电商市场分析专家，请分析以下品类数据。\n\n"
            f"## 品类\n{category}\n\n"
            f"## 新采集数据\n{raw_data}\n\n"
            f"{historical_context}\n\n"
            f"## 请输出\n"
            f"1. **市场容量评估** (TAM/SAM/SOM)\n"
            f"2. **竞品格局** (Top 3 竞品优劣势)\n"
            f"3. **价格带分布** (低档/中档/高档的比例)\n"
            f"4. **差评痛点 Top 5** (附频率)\n"
            f"5. **差异化切入推荐** (至少 2 个方向)\n"
            f"6. **增长趋势判断** (上升/平稳/下降)\n"
        )

        response = await self._llm_think(prompt, {})

        await self._memory.think(
            f"完成 {category} 市场分析, 发现关键洞察",
            importance=7,
        )

        return {
            "category": category,
            "analysis": response,
            "rag_sources_used": bool(historical_context),
        }

    async def cross_validate(
        self, claim: str, data_sources: list[str] | None = None
    ) -> dict[str, Any]:
        """
        交叉验证 — 用 RAG 检索多个数据源验证一个声明/数据点。
        
        例: CGO 说"宠物智能玩具月搜索量 50 万"，
        Analyst 会查历史数据、竞品数据、趋势数据来验证。
        """
        await self.initialize()
        rag = await get_rag()

        if data_sources is None:
            data_sources = ["products", "policies"]

        context = await rag.build_rag_context(
            query=claim,
            sources=data_sources,
            top_k=8,
        )

        prompt = (
            f"请验证以下声明的可靠性:\n\n"
            f"## 声明\n{claim}\n\n"
            f"{context}\n\n"
            f"## 请输出\n"
            f"1. **可信度评分** (1-10)\n"
            f"2. **支撑证据** (来自检索结果)\n"
            f"3. **反面证据** (如果有)\n"
            f"4. **结论**: 可信 / 部分可信 / 不可信\n"
        )

        response = await self._llm_think(prompt, {})

        await self._memory.think(
            f"交叉验证: {claim[:80]} → {response[:50]}",
            importance=6,
        )

        return {"claim": claim, "validation": response}

    async def generate_report(
        self, topic: str, data: dict[str, Any], report_type: str = "selection"
    ) -> dict[str, Any]:
        """
        生成结构化报告。
        
        report_type:
        - "selection": 选品报告
        - "competitor": 竞品分析报告
        - "trend": 趋势报告
        - "risk": 风险评估报告
        """
        await self.initialize()
        rag = await get_rag()

        # 根据报告类型决定 RAG 检索源
        source_map = {
            "selection": ["products", "policies"],
            "competitor": ["products"],
            "trend": ["products"],
            "risk": ["products", "policies"],
        }
        sources = source_map.get(report_type, ["products"])

        context = await rag.build_rag_context(
            query=topic,
            sources=sources,
            top_k=5,
        )

        template_map = {
            "selection": self._selection_report_prompt,
            "competitor": self._competitor_report_prompt,
            "trend": self._trend_report_prompt,
            "risk": self._risk_report_prompt,
        }

        prompt_fn = template_map.get(report_type, self._selection_report_prompt)
        prompt = prompt_fn(topic, data, context)

        response = await self._llm_think(prompt, {})

        await self._memory.think(
            f"生成了 {report_type} 报告: {topic[:60]}",
            importance=6,
        )

        return {
            "topic": topic,
            "report_type": report_type,
            "report": response,
        }

    async def ingest_and_index(self, data_type: str, data: dict[str, Any]) -> dict:
        """
        将数据向量化后存入知识库。
        Hunter 采集完数据后调用此方法。
        """
        await self.initialize()
        rag = await get_rag()

        ingest_fn = {
            "product": rag.ingest_product,
            "supplier": rag.ingest_supplier,
            "policy": rag.ingest_policy,
            "interaction": rag.ingest_interaction,
        }

        fn = ingest_fn.get(data_type)
        if not fn:
            return {"error": f"Unknown data_type: {data_type}"}

        result = await fn(data)

        await self._memory.think(
            f"向量化入库: {data_type} — {data.get('title', data.get('name', '?'))[:50]}",
            importance=4,
        )

        return {"indexed": True, "data_type": data_type, "result": result}

    # ─── Report Template Prompts ───

    @staticmethod
    def _selection_report_prompt(topic: str, data: dict, context: str) -> str:
        return (
            f"生成选品报告:\n\n"
            f"## 品类\n{topic}\n\n"
            f"## 数据\n{data}\n\n"
            f"{context}\n\n"
            f"## 报告格式\n"
            f"### 📊 机会概述\n### 🏪 市场数据\n### 🔍 竞品分析\n"
            f"### 😤 差评痛点\n### 💰 利润空间\n### 📈 增长策略\n### ⚠️ 风险提示\n"
        )

    @staticmethod
    def _competitor_report_prompt(topic: str, data: dict, context: str) -> str:
        return (
            f"生成竞品分析报告:\n\n"
            f"## 目标\n{topic}\n\n"
            f"## 数据\n{data}\n\n"
            f"{context}\n\n"
            f"## 报告格式\n"
            f"### 竞品概览\n### 差异化对比\n### SWOT\n### 建议策略\n"
        )

    @staticmethod
    def _trend_report_prompt(topic: str, data: dict, context: str) -> str:
        return (
            f"生成趋势报告:\n\n"
            f"## 领域\n{topic}\n\n"
            f"## 数据\n{data}\n\n"
            f"{context}\n\n"
            f"## 报告格式\n"
            f"### 趋势总览\n### 热门品类\n### 增长驱动因素\n### 窗口期判断\n"
        )

    @staticmethod
    def _risk_report_prompt(topic: str, data: dict, context: str) -> str:
        return (
            f"生成风险评估报告:\n\n"
            f"## 标的\n{topic}\n\n"
            f"## 数据\n{data}\n\n"
            f"{context}\n\n"
            f"## 报告格式\n"
            f"### 风险识别\n### 合规检查\n### 量化评分 (1-10)\n### 缓释建议\n"
        )
