"""
关系中台 — Sourcing Liaison 采购联络官 (L3)

职责：
- 供应商搜索与筛选
- 询价邮件起草与跟进
- 谈判策略建议
- 供应商关系档案维护 (CRM)
"""

from __future__ import annotations

from typing import Any

from src.platforms.base_worker import PlatformWorker
from src.platforms.data_intel.rag_pipeline import get_rag


class SourcingLiaisonAgent(PlatformWorker):
    """L3 关系中台 — 采购联络官"""

    ROLE = "l3_sourcing_liaison"
    DISPLAY_NAME = "采购联络官 (Sourcing Liaison)"
    LLM_ROLE = "coo"
    PLATFORM = "relationship"

    async def draft_inquiry_email(
        self,
        product_info: dict[str, Any],
        supplier_info: dict[str, Any] | None = None,
        tone: str = "professional",
    ) -> dict[str, Any]:
        """
        起草询价邮件。
        tone: "professional" | "friendly" | "firm" | "follow_up"
        """
        await self.initialize()
        rag = await get_rag()

        # 检索该供应商的历史沟通
        supplier_name = (supplier_info or {}).get("name", "")
        history_ctx = ""
        if supplier_name:
            history = await rag.search_interactions(f"supplier {supplier_name}", top_k=3)
            if history:
                history_ctx = "\n## 历史沟通\n" + "\n".join(
                    f"- [{h.get('direction', '?')}] {h.get('summary', '')[:100]}"
                    for h in history
                )

        prompt = (
            f"起草一封询价邮件。\n\n"
            f"## 产品需求\n{product_info}\n\n"
            f"## 供应商\n{supplier_info or '新供应商'}\n\n"
            f"{history_ctx}\n\n"
            f"## 语气: {tone}\n\n"
            f"## 要求\n"
            f"1. Subject 行 — 简洁专业\n"
            f"2. 自我介绍 (跨境电商公司)\n"
            f"3. 明确需求 (产品/规格/数量)\n"
            f"4. 索要: FOB 价格 / MOQ / 交期 / 样品政策\n"
            f"5. 预留谈判空间\n"
        )

        response = await self._llm_think(prompt, {})

        await self._memory.think(
            f"为 {supplier_name or '未知供应商'} 起草了询价邮件",
            importance=5,
        )

        # 记录交互
        if supplier_name:
            await rag.ingest_interaction({
                "contact_type": "SUPPLIER",
                "contact_name": supplier_name,
                "channel": "email",
                "direction": "outbound",
                "summary": f"询价邮件: {product_info.get('title', '')}",
            })

        return {"email_draft": response, "tone": tone, "requires_approval": True}

    async def suggest_negotiation_strategy(
        self, supplier_info: dict[str, Any], deal_context: dict[str, Any]
    ) -> dict[str, Any]:
        """基于历史数据和供应商画像，建议谈判策略。"""
        await self.initialize()
        rag = await get_rag()

        supplier_ctx = await rag.build_rag_context(
            query=supplier_info.get("name", ""),
            sources=["suppliers", "interactions"],
            top_k=5,
        )

        prompt = (
            f"制定谈判策略:\n\n"
            f"## 供应商\n{supplier_info}\n\n"
            f"## 交易背景\n{deal_context}\n\n"
            f"{supplier_ctx}\n\n"
            f"## 输出\n"
            f"1. 供应商谈判风格画像\n"
            f"2. 认为可争取的让步\n"
            f"3. 我方底线\n"
            f"4. 开场策略\n"
            f"5. 备选方案 (BATNA)\n"
        )

        response = await self._llm_think(prompt, {})
        return {"strategy": response}

    async def search_suppliers(
        self, product_requirements: str, region: str = "China"
    ) -> dict[str, Any]:
        """搜索符合需求的供应商 (RAG + 爬虫)。"""
        await self.initialize()
        rag = await get_rag()

        existing = await rag.search_suppliers(product_requirements, top_k=5)

        prompt = (
            f"搜索供应商:\n\n"
            f"## 需求\n{product_requirements}\n\n"
            f"## 区域: {region}\n\n"
            f"## 已知供应商\n{existing}\n\n"
            f"## 输出\n"
            f"1. 推荐渠道 (1688/Alibaba/展会/行业协会)\n"
            f"2. 搜索关键词建议\n"
            f"3. 筛选标准 (最低资质)\n"
            f"4. 如果已知供应商中有合适的，标注出来\n"
        )

        response = await self._llm_think(prompt, {})
        return {"search_results": response, "known_matches": len(existing)}
