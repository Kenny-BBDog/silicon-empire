"""
Outcome Tracker — 决策结果追踪，闭环验证。

每次 Agent 做出预测性决策时:
1. record_prediction() — 记录预测
2. (等结果出来后)
3. evaluate_outcome() — 评估准确性 + 提炼教训
4. 教训自动写入知识库

这是进化闭环的核心 — 没有结果验证的进化是盲目的。
"""

from __future__ import annotations

import logging
from typing import Any
from datetime import datetime, timezone

logger = logging.getLogger("outcome_tracker")


class OutcomeTracker:
    """追踪决策预测与实际结果。"""

    async def _get_db(self):
        from src.core.memory import get_memory
        return await get_memory()

    async def record_prediction(
        self,
        decision_id: str,
        agent_role: str,
        prediction: str,
    ) -> dict[str, Any]:
        """
        决策时记录预测。

        例: CGO 预测 "宠物品类 Q2 增长 25%"
        """
        mem = await self._get_db()
        return await mem.insert_row("decision_outcomes", {
            "decision_id": decision_id,
            "agent_role": agent_role,
            "prediction": prediction,
        })

    async def evaluate_outcome(
        self,
        decision_id: str,
        actual_result: str,
        agent_role: str | None = None,
    ) -> dict[str, Any]:
        """
        结果出来后评估预测准确性。

        自动:
        1. 计算准确度
        2. 提炼教训
        3. 写入知识库
        """
        mem = await self._get_db()

        # 查找原始预测
        predictions = await mem.query_table(
            "decision_outcomes",
            filters={"decision_id": decision_id},
        )

        if not predictions:
            return {"error": "no prediction found for this decision"}

        for pred in predictions:
            if agent_role and pred.get("agent_role") != agent_role:
                continue

            # LLM 评估准确性
            accuracy, lesson = await self._evaluate_with_llm(
                pred.get("prediction", ""),
                actual_result,
                pred.get("agent_role", ""),
            )

            # 更新记录
            await mem.update_row(
                "decision_outcomes",
                match={"id": pred["id"]},
                data={
                    "actual_result": actual_result,
                    "accuracy_score": accuracy,
                    "lessons_learned": lesson,
                },
            )

            # 教训写入知识库
            if lesson:
                try:
                    from src.core.knowledge_base import get_knowledge_base
                    kb = await get_knowledge_base()
                    await kb.learn(
                        category="lesson",
                        title=f"{pred.get('agent_role', '?')} 的决策复盘",
                        content=f"预测: {pred.get('prediction', '')[:100]}\n"
                                f"实际: {actual_result[:100]}\n"
                                f"教训: {lesson}",
                        source_agent=pred.get("agent_role", "system"),
                        confidence=0.9,
                    )
                except Exception as e:
                    logger.error(f"Failed to write lesson: {e}")

        return {"evaluated": len(predictions), "decision_id": decision_id}

    async def _evaluate_with_llm(
        self,
        prediction: str,
        actual: str,
        role: str,
    ) -> tuple[float, str]:
        """用 LLM 评估预测准确性。"""
        try:
            from src.core.llm_gateway import get_llm
            from langchain_core.messages import HumanMessage

            llm = get_llm("analysis")
            response = await llm.ainvoke([HumanMessage(content=(
                f"评估以下预测的准确性:\n\n"
                f"预测: {prediction}\n"
                f"实际结果: {actual}\n\n"
                f"给出:\n"
                f"1. ACCURACY: 0-1 之间的数字\n"
                f"2. LESSON: 一句话教训\n"
            ))])

            text = response.content
            accuracy = 0.5
            lesson = ""

            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("ACCURACY:"):
                    try:
                        accuracy = float(line.replace("ACCURACY:", "").strip())
                    except ValueError:
                        pass
                elif line.startswith("LESSON:"):
                    lesson = line.replace("LESSON:", "").strip()

            return accuracy, lesson

        except Exception:
            return 0.5, "无法自动评估"

    async def get_agent_accuracy(self, agent_role: str, limit: int = 20) -> float:
        """获取 Agent 近期预测准确率。"""
        mem = await self._get_db()
        outcomes = await mem.query_table(
            "decision_outcomes",
            filters={"agent_role": agent_role},
            limit=limit,
        )
        if not outcomes:
            return 0.5

        scores = [o["accuracy_score"] for o in outcomes if o.get("accuracy_score")]
        return sum(scores) / len(scores) if scores else 0.5


# Singleton
_tracker: OutcomeTracker | None = None


async def get_outcome_tracker() -> OutcomeTracker:
    global _tracker
    if _tracker is None:
        _tracker = OutcomeTracker()
    return _tracker
