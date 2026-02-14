"""
L2 Chief Operating Officer (COO) — Cost precision, P&L modeling, operational efficiency.
"""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent
from src.core.state import SiliconState, CritiqueEntry


class COOAgent(BaseAgent):
    ROLE = "coo"
    DISPLAY_NAME = "首席运营官 (COO)"
    LLM_ROLE = "coo"

    async def review_proposal(self, state: SiliconState) -> dict[str, Any]:
        """
        Joint Session: Analyze cost structure and calculate profitability.
        Writes to critique_logs.coo.
        """
        await self.initialize()

        proposal = state.proposal_buffer[-1] if state.proposal_buffer else {}

        prompt = (
            f"你是 COO，审查以下提案的成本结构和利润率。\n\n"
            f"## 提案\n{proposal.get('content', '无提案')}\n\n"
            f"## 你的任务\n"
            f"按照你的输出格式模板回复，必须包含：\n"
            f"- 成本分析表格 (采购成本/运费/仓储/佣金/广告)\n"
            f"- 利润计算 (毛利/净利/盈亏平衡)\n"
            f"- 最终结论 (APPROVE / REJECT / 建议调整)\n\n"
            f"你的数字必须可追溯，利润率 < 15% 必须 REJECT。"
        )

        response = await self._llm_think(prompt, {})

        # Determine verdict from response
        verdict = "APPROVE"
        if "REJECT" in response.upper():
            verdict = "REJECT"
        elif "VETO" in response.upper():
            verdict = "VETO"

        return {
            "review": response,
            "reviewer": "coo",
            "verdict": verdict,
            "critique_entry": CritiqueEntry(
                verdict=verdict,
                analysis=response,
            ).model_dump(),
        }

    async def debate(self, state: SiliconState, round_num: int) -> dict[str, Any]:
        """Hearing Round 3: Arbitrate — P&L model based on CGO and CRO arguments."""
        await self.initialize()

        transcript = "\n".join(
            f"**Round {t['round']} ({t['speaker']})**: {t['content'][:400]}"
            for t in state.meeting_transcript
        )

        prompt = (
            f"这是对抗性听证会 **Round 3**。你是**仲裁方**。\n\n"
            f"## 议题\n{state.strategic_intent}\n\n"
            f"## 前两轮发言\n{transcript}\n\n"
            f"## 你的任务\n"
            f"基于 CGO 的利好和 CRO 的风险，提供：\n"
            f"1. 完整 P&L 模型\n"
            f"2. 盈亏平衡点分析\n"
            f"3. 资金占用评估\n"
            f"4. 回本周期\n\n"
            f"必须用精确的数字，不能模糊。"
        )

        response = await self._llm_think(prompt, {})
        return {
            "round": 3,
            "speaker": self.DISPLAY_NAME,
            "role_in_debate": "仲裁方",
            "content": response,
        }
