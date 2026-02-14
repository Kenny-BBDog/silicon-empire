"""
L2 Chief Technology Officer (CTO) — Tech enablement, tool management, self-healing.
"""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent
from src.core.state import SiliconState, CritiqueEntry


class CTOAgent(BaseAgent):
    ROLE = "cto"
    DISPLAY_NAME = "首席技术官 (CTO)"
    LLM_ROLE = "cto"

    async def review_proposal(self, state: SiliconState) -> dict[str, Any]:
        """
        Joint Session: Evaluate technical feasibility.
        Writes to critique_logs.cto.
        """
        await self.initialize()

        proposal = state.proposal_buffer[-1] if state.proposal_buffer else {}

        prompt = (
            f"你是 CTO，评估以下提案的技术可行性。\n\n"
            f"## 提案\n{proposal.get('content', '无提案')}\n\n"
            f"## 你的任务\n"
            f"按照你的输出格式模板回复，必须包含：\n"
            f"- 中台就绪度表格 (各能力的状态)\n"
            f"- 开发需求 (需新开发/适配的工具)\n"
            f"- 基础设施评估 (API 限流/第三方依赖)\n"
            f"- 最终结论 (YES / YES_WITH_WORK / NO)\n\n"
            f"你的评估必须诚实，不夸大也不隐瞒困难。"
        )

        response = await self._llm_think(prompt, {})

        # Determine verdict
        verdict = "APPROVE"
        if "NO" in response.upper().split() and "YES" not in response.upper():
            verdict = "REJECT"
        elif "VETO" in response.upper():
            verdict = "VETO"

        return {
            "review": response,
            "reviewer": "cto",
            "verdict": verdict,
            "critique_entry": CritiqueEntry(
                verdict=verdict,
                analysis=response,
            ).model_dump(),
        }

    async def debate(self, state: SiliconState, round_num: int) -> dict[str, Any]:
        """Hearing Round 4: Technical feasibility assessment."""
        await self.initialize()

        transcript = "\n".join(
            f"**Round {t['round']} ({t['speaker']})**: {t['content'][:400]}"
            for t in state.meeting_transcript
        )

        prompt = (
            f"这是对抗性听证会 **Round 4**。你是**技术方**。\n\n"
            f"## 议题\n{state.strategic_intent}\n\n"
            f"## 前三轮发言\n{transcript}\n\n"
            f"## 你的任务\n"
            f"综合前三位首席的辩论，给出技术评估：\n"
            f"1. 实现周期\n"
            f"2. 所需新工具/适配\n"
            f"3. 技术风险\n"
            f"4. 中台就绪度\n"
            f"5. API/第三方依赖稳定性\n"
            f"6. 推荐实施路径\n\n"
            f"你只做技术判断，不参与商业博弈。"
        )

        response = await self._llm_think(prompt, {})
        return {
            "round": 4,
            "speaker": self.DISPLAY_NAME,
            "role_in_debate": "技术方",
            "content": response,
        }

    async def diagnose_error(self, state: SiliconState) -> dict[str, Any]:
        """Self-Healing entry: diagnose an error from L3 platforms."""
        await self.initialize()

        error = state.error_log or {}

        prompt = (
            f"L3 中台报告了一个错误。\n\n"
            f"## 错误信息\n```\n{error}\n```\n\n"
            f"## 判断\n"
            f"1. 这是临时故障(网络/限流) → 建议 RETRY\n"
            f"2. 这是逻辑错误(API变更/反爬) → 建议 REBUILD\n"
            f"3. 这是配置问题 → 建议 CONFIG_FIX\n\n"
            f"返回诊断结论和建议行动。"
        )

        response = await self._llm_think(prompt, {})
        return {"diagnosis": response}
