"""
L1 General Manager (GM) — Central router, moderator, and summarizer.
"""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent
from src.core.state import SiliconState, DecisionMatrix
from src.core.guards import auto_judge


class GMAgent(BaseAgent):
    ROLE = "gm"
    DISPLAY_NAME = "总经理 (GM)"
    LLM_ROLE = "gm"

    # ─── Intent Parsing ───

    async def parse_intent(self, state: SiliconState) -> dict[str, Any]:
        """Parse L0's natural language intent into structured category."""
        await self.initialize()

        prompt = (
            f"分析以下用户意图，返回一个 JSON 对象：\n\n"
            f"用户意图: {state.strategic_intent}\n\n"
            f"请返回：\n"
            f'- "intent_category": 从以下选择一个：\n'
            f"  NEW_CATEGORY (新赛道/品类探索)\n"
            f"  PRODUCT_LAUNCH (具体产品上架)\n"
            f"  SOURCING (采购/供应商相关)\n"
            f"  TECH_FIX (技术问题/工具修复)\n"
            f"  COMPLEX_STRATEGY (复杂战略决策)\n"
            f'- "mode": EXPLORATION 或 EXECUTION\n'
            f'- "meeting_type": EXPLORATION_CHAT, ASYNC_JOINT, 或 ADVERSARIAL_HEARING\n'
            f'- "reasoning": 简要说明判断理由\n'
        )

        response = await self._llm_think(prompt, {})
        return {"intent_parsed": response}

    def route_mode(self, state: SiliconState) -> str:
        """
        Determine operating mode based on intent category.
        Used as a LangGraph conditional_edge function.
        """
        category = state.intent_category

        if category in ("NEW_CATEGORY", "COMPLEX_STRATEGY"):
            return "exploration"
        elif category == "TECH_FIX":
            return "self_heal"
        else:
            return "execution"

    # ─── Meeting Moderation ───

    async def check_convergence(self, state: SiliconState) -> str:
        """
        Check if exploration discussion has converged.
        Returns: "converged" or "continue"
        """
        await self.initialize()

        transcript = "\n".join(
            f"**{t['speaker']}** (Round {t['round']}): {t['content'][:300]}"
            for t in state.meeting_transcript
        )

        prompt = (
            f"作为 GM，判断此讨论是否已收敛到可提交的提案。\n\n"
            f"## 原始议题\n{state.strategic_intent}\n\n"
            f"## 讨论记录\n{transcript}\n\n"
            f"## 判断标准\n"
            f"1. 四方都至少发言 1 次\n"
            f"2. 核心分歧已明确\n"
            f"3. 已形成可提交的行动方案\n\n"
            f"回答 CONVERGED 或 CONTINUE，附简要理由。"
        )

        response = await self._llm_think(prompt, {})
        return "converged" if "CONVERGED" in response.upper() else "continue"

    async def aggregate_reviews(self, state: SiliconState) -> dict[str, Any]:
        """
        Aggregate all C-Suite reviews into decision_matrix.
        Used after parallel reviews in Async Joint Session.
        """
        await self.initialize()

        critiques_summary = "\n".join(
            f"**{role.upper()}**: verdict={entry.verdict}, analysis={entry.analysis[:200]}"
            for role, entry in state.critique_logs.items()
        )

        prompt = (
            f"汇总以下三位首席官的审查意见，生成结构化决策矩阵。\n\n"
            f"## 审查结果\n{critiques_summary}\n\n"
            f"请返回：\n"
            f'- "profit_pct": 预估利润率(%)\n'
            f'- "risk_score": 风险分(1-5)\n'
            f'- "tech_ready": 技术是否就绪(true/false)\n'
            f'- "consensus": 是否达成共识(true/false)\n'
            f'- "summary": 一句话总结\n'
        )

        response = await self._llm_think(prompt, {})
        return {"aggregation": response}

    def judge_decision(self, state: SiliconState) -> str:
        """
        Apply auto-judge logic to determine next step.
        Returns: "auto_approve" | "revise" | "escalate"
        """
        return auto_judge(state)

    # ─── Hearing Summary ───

    async def summarize_hearing(self, state: SiliconState) -> dict[str, Any]:
        """Generate Feishu card content for L0 decision after hearing."""
        await self.initialize()

        transcript = "\n".join(
            f"### Round {t['round']} ({t['speaker']})\n{t['content']}"
            for t in state.meeting_transcript
        )

        prompt = (
            f"将以下听证会辩论汇总为飞书决策卡片内容。\n\n"
            f"## 议题\n{state.strategic_intent}\n\n"
            f"## 辩论全文\n{transcript}\n\n"
            f"## 输出格式\n"
            f"📈 CGO 观点：[摘要]\n"
            f"🛡️ CRO 警告：[摘要]\n"
            f"📊 COO 核算：[摘要]\n"
            f"⚙️ CTO 评估：[摘要]\n"
        )

        response = await self._llm_think(prompt, {})
        return {"hearing_summary": response}
