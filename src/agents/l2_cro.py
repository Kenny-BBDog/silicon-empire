"""
L2 Chief Risk Officer (CRO) — Compliance, IP detection, zero-tolerance risk management.
"""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent
from src.core.state import SiliconState, CritiqueEntry


class CROAgent(BaseAgent):
    ROLE = "cro"
    DISPLAY_NAME = "首席风控官 (CRO)"
    LLM_ROLE = "cro"

    async def review_proposal(self, state: SiliconState) -> dict[str, Any]:
        """
        Joint Session: Audit compliance and IP risks.
        Writes to critique_logs.cro.
        """
        await self.initialize()

        proposal = state.proposal_buffer[-1] if state.proposal_buffer else {}

        prompt = (
            f"你是 CRO，审查以下提案的合规和知产风险。\n\n"
            f"## 提案\n{proposal.get('content', '无提案')}\n\n"
            f"## 你的任务\n"
            f"按照你的输出格式模板回复，必须包含：\n"
            f"- 平台合规检查 (品类/文案/图片)\n"
            f"- 知识产权检查 (专利/商标)\n"
            f"- 历史教训引用\n"
            f"- 风险评分 (1-5)\n"
            f"- 最终结论 (APPROVE / REJECT / 需修改)\n\n"
            f"**你必须引用具体政策条款**，禁止模糊表述。\n"
            f"风险分 ≥ 4 必须投 VETO。"
        )

        response = await self._llm_think(prompt, {})

        # Parse risk score and determine verdict
        verdict = "APPROVE"
        if "VETO" in response.upper():
            verdict = "VETO"
        elif "REJECT" in response.upper():
            verdict = "REJECT"

        return {
            "review": response,
            "reviewer": "cro",
            "verdict": verdict,
            "critique_entry": CritiqueEntry(
                verdict=verdict,
                analysis=response,
            ).model_dump(),
        }

    async def debate(self, state: SiliconState, round_num: int) -> dict[str, Any]:
        """Hearing Round 2: Defend — refute CGO point by point with policy citations."""
        await self.initialize()

        # Get CGO's Round 1 content
        cgo_argument = ""
        for t in state.meeting_transcript:
            if t.get("round") == 1:
                cgo_argument = t.get("content", "")
                break

        prompt = (
            f"这是对抗性听证会 **Round 2**。你是**防守方**。\n\n"
            f"## 议题\n{state.strategic_intent}\n\n"
            f"## CGO 的 Round 1 利好报告\n{cgo_argument}\n\n"
            f"## 你的任务\n"
            f"逐条反驳 CGO 的观点：\n"
            f"1. **必须引用 mem_policies 中的具体政策条款**\n"
            f"2. 列出封号/侵权的历史案例\n"
            f"3. 每个风险点给出风险等级\n"
            f"4. 给出综合风险评分 (1-5)\n\n"
            f"你不考虑利润，只考虑风险。"
        )

        response = await self._llm_think(prompt, {})
        return {
            "round": 2,
            "speaker": self.DISPLAY_NAME,
            "role_in_debate": "防守方",
            "content": response,
        }
