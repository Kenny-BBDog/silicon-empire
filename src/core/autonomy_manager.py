"""
Autonomy Manager — 渐进自治系统。

系统从"全部需要老板批准"逐步进化到"日常自理":

Level 0: 所有决策需老板批准 (初始状态)
Level 1: 常规选品 GM 自批，重大变更老板批
Level 2: 日常运营全自治，战略方向老板批
Level 3: 完全自治 (保留老板否决权)

升级条件: 连续 N 次决策准确率 > 阈值
降级条件: 出现重大失误 或 老板手动降级
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("autonomy")

# 升级阈值
UPGRADE_THRESHOLDS = {
    0: {"min_decisions": 10, "min_accuracy": 0.7},   # 0→1
    1: {"min_decisions": 30, "min_accuracy": 0.8},   # 1→2
    2: {"min_decisions": 100, "min_accuracy": 0.85},  # 2→3
}


class AutonomyManager:
    """管理系统自治等级。"""

    async def _get_db(self):
        from src.core.memory import get_memory
        return await get_memory()

    async def get_current_level(self) -> int:
        """获取当前自治等级。"""
        mem = await self._get_db()
        results = await mem.query_table("autonomy_levels", limit=1)
        if results:
            return results[0].get("current_level", 0)
        return 0

    async def should_auto_approve(self, decision_risk: int) -> bool:
        """
        根据当前自治等级判断是否可以自动批准。
        
        risk 1-5:
        - Level 0: 全部需批准
        - Level 1: risk <= 2 自动批
        - Level 2: risk <= 3 自动批
        - Level 3: risk <= 4 自动批 (risk 5 始终需老板)
        """
        level = await self.get_current_level()

        auto_approve_map = {
            0: 0,    # 永远不自动批
            1: 2,    # 低风险自动批
            2: 3,    # 中风险也自动批
            3: 4,    # 高风险也自动批
        }

        max_auto_risk = auto_approve_map.get(level, 0)
        return decision_risk <= max_auto_risk

    async def check_upgrade(self) -> dict[str, Any]:
        """
        检查是否满足升级条件。
        由调度器定期触发。
        """
        current_level = await self.get_current_level()
        if current_level >= 3:
            return {"action": "none", "reason": "已达最高等级"}

        threshold = UPGRADE_THRESHOLDS.get(current_level)
        if not threshold:
            return {"action": "none", "reason": "无可用阈值"}

        mem = await self._get_db()
        outcomes = await mem.query_table(
            "decision_outcomes",
            limit=threshold["min_decisions"],
        )

        if len(outcomes) < threshold["min_decisions"]:
            return {
                "action": "wait",
                "reason": f"样本不足: {len(outcomes)}/{threshold['min_decisions']}",
            }

        scores = [o["accuracy_score"] for o in outcomes if o.get("accuracy_score")]
        if not scores:
            return {"action": "wait", "reason": "无评分数据"}

        avg_accuracy = sum(scores) / len(scores)

        if avg_accuracy >= threshold["min_accuracy"]:
            return {
                "action": "upgrade",
                "from": current_level,
                "to": current_level + 1,
                "accuracy": round(avg_accuracy, 3),
                "reason": f"准确率 {avg_accuracy:.1%} ≥ {threshold['min_accuracy']:.0%}",
            }

        return {
            "action": "hold",
            "accuracy": round(avg_accuracy, 3),
            "required": threshold["min_accuracy"],
            "reason": f"准确率 {avg_accuracy:.1%} < {threshold['min_accuracy']:.0%}",
        }

    async def upgrade(self, reason: str = "") -> int:
        """升级自治等级。"""
        current = await self.get_current_level()
        new_level = min(current + 1, 3)

        mem = await self._get_db()
        await mem.insert_row("autonomy_levels", {
            "current_level": new_level,
            "upgrade_reason": reason,
        })

        logger.info(f"Autonomy upgraded: {current} → {new_level} ({reason})")
        return new_level

    async def downgrade(self, reason: str = "") -> int:
        """降级自治等级 (老板或系统触发)。"""
        current = await self.get_current_level()
        new_level = max(current - 1, 0)

        mem = await self._get_db()
        await mem.insert_row("autonomy_levels", {
            "current_level": new_level,
            "downgrade_reason": reason,
        })

        logger.info(f"Autonomy downgraded: {current} → {new_level} ({reason})")
        return new_level


# Singleton
_manager: AutonomyManager | None = None


async def get_autonomy_manager() -> AutonomyManager:
    global _manager
    if _manager is None:
        _manager = AutonomyManager()
    return _manager
