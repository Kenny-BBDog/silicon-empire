"""
Capability Scoring — Agent 能力评分系统。

基于 decision_outcomes 数据，为每个 Agent 计算多维能力分:
- accuracy: 预测准确率
- speed: 响应速度 (未来实现)
- collaboration: 协作评分 (被多少人引用/问)
- innovation: 创新度 (提出了多少被采纳的新想法)

能力分影响:
1. 会议中的投票权重
2. 任务分配优先级
3. 自治等级升降
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("capability")


class CapabilityScorer:
    """计算和追踪 Agent 能力分。"""

    DIMENSIONS = ["accuracy", "speed", "collaboration", "innovation"]

    async def _get_db(self):
        from src.core.memory import get_memory
        return await get_memory()

    async def compute_score(self, agent_role: str) -> dict[str, float]:
        """计算某个 Agent 的全维度能力分。"""
        scores = {}

        # Accuracy: 基于 outcome_tracker
        scores["accuracy"] = await self._compute_accuracy(agent_role)

        # Collaboration: 基于被引用次数
        scores["collaboration"] = await self._compute_collaboration(agent_role)

        # Speed + Innovation: 暂用默认值
        scores["speed"] = 70.0
        scores["innovation"] = 60.0

        # 保存快照
        await self._save_snapshot(agent_role, scores)

        return scores

    async def _compute_accuracy(self, role: str) -> float:
        """基于预测准确率计算。"""
        try:
            from src.core.outcome_tracker import get_outcome_tracker
            tracker = await get_outcome_tracker()
            raw = await tracker.get_agent_accuracy(role)
            return round(raw * 100, 1)
        except Exception:
            return 50.0

    async def _compute_collaboration(self, role: str) -> float:
        """基于消息交互频率。"""
        try:
            from src.core.agent_bus import get_message_log
            msgs = await get_message_log(limit=200)
            # 计算被别人提问/请教的次数
            asked = sum(1 for m in msgs if m.get("receiver") == role and m.get("msg_type") == "question")
            # 每 10 次算 10 分，满分 100
            return min(100.0, asked * 10.0)
        except Exception:
            return 50.0

    async def _save_snapshot(self, role: str, scores: dict[str, float]) -> None:
        """保存能力分快照。"""
        try:
            mem = await self._get_db()
            for dim, score in scores.items():
                await mem.insert_row("agent_capability_scores", {
                    "agent_role": role,
                    "dimension": dim,
                    "score": score,
                })
        except Exception as e:
            logger.error(f"Failed to save capability snapshot: {e}")

    async def get_latest_scores(self, agent_role: str) -> dict[str, float]:
        """获取最新能力分。"""
        mem = await self._get_db()
        scores = {}
        for dim in self.DIMENSIONS:
            results = await mem.query_table(
                "agent_capability_scores",
                filters={"agent_role": agent_role, "dimension": dim},
                limit=1,
            )
            if results:
                scores[dim] = results[0].get("score", 50.0)
            else:
                scores[dim] = 50.0
        return scores

    async def get_voting_weight(self, agent_role: str) -> float:
        """
        基于能力分计算投票权重。
        
        用于会议系统 — 准确率高的 Agent 意见权重更高。
        返回 0.5 - 1.5 的权重系数。
        """
        scores = await self.get_latest_scores(agent_role)
        avg = sum(scores.values()) / len(scores) if scores else 50.0
        # 映射到 0.5 - 1.5
        return 0.5 + (avg / 100.0)


# Singleton
_scorer: CapabilityScorer | None = None


async def get_capability_scorer() -> CapabilityScorer:
    global _scorer
    if _scorer is None:
        _scorer = CapabilityScorer()
    return _scorer
