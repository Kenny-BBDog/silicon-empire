"""
L2 Chief Growth Officer (CGO) — Aggressive growth, product discovery, GMV maximization.
"""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent
from src.core.state import SiliconState, CritiqueEntry


class CGOAgent(BaseAgent):
    ROLE = "cgo"
    DISPLAY_NAME = "首席增长官 (CGO)"
    LLM_ROLE = "cgo"

    async def generate_proposal(self, state: SiliconState) -> dict[str, Any]:
        """
        Generate a product/strategy proposal based on the strategic intent.
        This is the primary action in both Joint Session and Hearing Round 1.
        """
        await self.initialize()

        # Try skill-based execution first
        from src.skills.loader import match_skill
        skill = match_skill(self._skills, state.intent_category, state.strategic_intent)

        if skill:
            result = await self._execute_skill(skill, state)
            return {
                "proposal": result,
                "skill_used": skill.name,
                "author": "CGO",
            }

        # Fallback to free-form proposal
        prompt = (
            f"你是 CGO，需要针对以下意图生成一份完整的商业提案。\n\n"
            f"## 意图\n{state.strategic_intent}\n\n"
            f"## 输出要求\n"
            f"按照你的输出格式模板回复，必须包含：\n"
            f"- 机会概述\n"
            f"- 市场数据\n"
            f"- 增长策略\n"
            f"- 风险容忍声明\n"
        )

        if state.iteration_count > 0 and state.critique_logs:
            prompt += "\n\n## 上一轮反馈\n"
            for role, critique in state.critique_logs.items():
                if critique.analysis:
                    prompt += f"**{role.upper()}**: {critique.analysis[:300]}\n"
            prompt += "\n请针对以上反馈修改你的提案。"

        response = await self._llm_think(prompt, {})
        return {"proposal": response, "author": "CGO"}

    async def review_proposal(self, state: SiliconState) -> dict[str, Any]:
        """CGO doesn't review its own proposals in joint session."""
        return {"review": "N/A — CGO is the proposer", "reviewer": "cgo"}

    async def debate(self, state: SiliconState, round_num: int) -> dict[str, Any]:
        """Hearing Round 1: Attack — present growth opportunity report."""
        await self.initialize()

        prompt = (
            f"这是对抗性听证会 **Round 1**。你是**进攻方**。\n\n"
            f"## 议题\n{state.strategic_intent}\n\n"
            f"## 你的任务\n"
            f"提交利好报告，必须包含：\n"
            f"1. 市场数据（规模、增长率、竞品数量）\n"
            f"2. 增长预测（预估月销量、GMV）\n"
            f"3. 竞品空白（差异化机会）\n"
            f"4. 差异化策略\n\n"
            f"用数据说话，要有说服力。"
        )

        response = await self._llm_think(prompt, {})
        return {
            "round": 1,
            "speaker": self.DISPLAY_NAME,
            "role_in_debate": "进攻方",
            "content": response,
        }
