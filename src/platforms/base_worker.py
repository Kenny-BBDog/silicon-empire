"""
L3 Platform Worker — base class for all L3 middle-platform agents.

L3 员工与 L2 首席的区别：
- L2 是决策者 (CGO/COO/CRO/CTO)，调用 L3 服务
- L3 是执行者 (Hunter/Analyst/Copywriter 等)，被 L2 委派任务

共同点：
- 都有个人记忆 (PersonalMemory)
- 都支持 Skill 和 MCP
- 都可以参与放假模式聊天

差异点：
- L3 任务通常来自 L2 委派或定时触发，不直接参与联席会/听证会
- L3 有专属的 execution context (关注"怎么做"而非"做不做")
"""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent
from src.core.state import SiliconState


class PlatformWorker(BaseAgent):
    """
    Base class for L3 middle-platform workers.
    Inherits all BaseAgent capabilities (personal memory, skills, MCP).
    """

    PLATFORM: str = ""   # e.g. "data_intel", "creative", "bizops"

    async def execute_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a delegated task from L2.
        
        Args:
            task: {
                "task_type": "scrape_category" | "analyze_data" | ...,
                "params": {...},
                "delegated_by": "cgo",
                "trace_id": "...",
            }
        
        Returns:
            Execution result dict.
        """
        await self.initialize()

        task_type = task.get("task_type", "")
        params = task.get("params", {})

        # Record task in personal memory
        await self._memory.think(
            f"收到 {task.get('delegated_by', '?')} 的委派任务: {task_type}",
            importance=5,
        )

        # Try skill match
        from src.skills.loader import match_skill
        skill = match_skill(self._skills, task_type, str(params))

        if skill:
            result = await self._execute_skill(skill, self._task_to_state(task))
            await self._memory.think(
                f"用 Skill [{skill.name}] 完成了 {task_type}",
                importance=5,
            )
            return result

        # Fallback: persistent execution (retry + decompose + escalate)
        try:
            from src.core.persistence import persistent_execute
            result = await persistent_execute(self, task)
        except Exception:
            result = await self._execute_freeform(task)
        return result

    async def _execute_freeform(self, task: dict[str, Any]) -> dict[str, Any]:
        """Free-form task execution when no Skill matches."""
        prompt = (
            f"你需要完成以下任务:\n\n"
            f"## 任务类型\n{task.get('task_type', '未指定')}\n\n"
            f"## 参数\n{task.get('params', {})}\n\n"
            f"## 委派方\n{task.get('delegated_by', '未知')}\n\n"
            f"请按照你的专业能力执行，输出结构化结果。"
        )
        response = await self._llm_think(prompt, {})
        return {"result": response, "task_type": task.get("task_type", "")}

    @staticmethod
    def _task_to_state(task: dict[str, Any]) -> SiliconState:
        """Convert a task dict to a minimal SiliconState for skill execution."""
        return SiliconState(
            trace_id=task.get("trace_id", ""),
            strategic_intent=str(task.get("params", {})),
            intent_category=task.get("task_type", ""),
        )
