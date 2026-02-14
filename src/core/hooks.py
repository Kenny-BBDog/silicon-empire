"""
Agent Lifecycle Hooks — 让 Agent 活起来。

不是被动等命令，而是在关键时刻自动思考:
- after_task: 任务完成后反思 — 缺什么工具？缺什么数据？
- on_error: 出错后诊断 — 是资源不足？还是能力不足？
- periodic: 定期自省 — 有什么可以改进？需要什么资源？

每次触发 Hook 产生的需求 → 写入 needs_queue → 定期由 GM 整理上报。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


# ─── 全局需求队列 (内存 + 持久化) ───

_needs_queue: list[dict[str, Any]] = []


def get_needs_queue() -> list[dict[str, Any]]:
    """获取当前需求队列。"""
    return _needs_queue.copy()


def clear_needs_queue() -> list[dict[str, Any]]:
    """清空并返回队列。GM 整理后调用。"""
    global _needs_queue
    current = _needs_queue.copy()
    _needs_queue = []
    return current


def submit_need(
    agent_role: str,
    category: str,
    title: str,
    description: str,
    priority: str = "P2",
    target: str = "gm",
) -> dict[str, Any]:
    """
    Agent 提交需求。

    category:
        resource    — 服务器/存储/网络/API额度
        tool        — 新工具/MCP/API
        skill       — 新技能/工作流
        agent       — 新下属Agent
        data        — 新数据源/数据库
        optimize    — 优化现有能力
        infra       — 基础设施升级

    target: gm / boss / cto
    """
    need = {
        "id": f"need-{len(_needs_queue)+1:04d}",
        "agent_role": agent_role,
        "category": category,
        "title": title,
        "description": description,
        "priority": priority,
        "target": target,
        "status": "pending",  # pending / reviewed / approved / resolved
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    _needs_queue.append(need)
    return need


# ─── Lifecycle Hook 方法 (mixin 注入到 BaseAgent) ───

async def after_task_hook(agent, task_result: dict[str, Any], task_context: dict[str, Any]):
    """
    任务完成后自动触发:
    Agent 反思"刚才做这个任务，有没有缺什么？"
    """
    try:
        prompt = (
            f"你刚完成了一个任务。反思以下问题:\n\n"
            f"任务结果摘要: {str(task_result)[:300]}\n\n"
            f"思考:\n"
            f"1. 做这个任务时，有没有缺少什么工具或数据？\n"
            f"2. 有没有什么重复性工作可以自动化？\n"
            f"3. 有没有什么资源（服务器/存储/API）不够用？\n"
            f"4. 有没有需要新建的Agent来帮你做事？\n\n"
            f"如果一切顺利不需要什么，回复 'NONE'。\n"
            f"如果有需求，用以下格式 (可多条):\n"
            f"NEED|category|priority|title|description\n"
            f"category: resource/tool/skill/agent/data/optimize/infra\n"
            f"priority: P0/P1/P2"
        )

        response = await agent._llm_think(prompt, {})

        # 解析需求
        if "NONE" not in response.upper() or "NEED|" in response:
            for line in response.strip().split("\n"):
                if line.startswith("NEED|"):
                    parts = line.split("|")
                    if len(parts) >= 5:
                        submit_need(
                            agent_role=agent.ROLE,
                            category=parts[1].strip(),
                            priority=parts[2].strip(),
                            title=parts[3].strip(),
                            description=parts[4].strip(),
                        )
    except Exception:
        pass  # Hook failure should never block task


async def on_error_hook(agent, error: Exception, context: dict[str, Any]):
    """
    出错后自动触发:
    Agent 判断"是我能力不足，还是资源不足？"
    """
    try:
        error_msg = str(error)[:200]

        # 常见资源不足模式
        if any(kw in error_msg.lower() for kw in ["quota", "rate limit", "timeout", "disk", "memory", "oom"]):
            submit_need(
                agent_role=agent.ROLE,
                category="resource",
                priority="P1",
                title=f"资源不足: {error_msg[:50]}",
                description=f"执行任务时遇到资源限制: {error_msg}",
            )
        elif any(kw in error_msg.lower() for kw in ["not found", "no such", "missing"]):
            submit_need(
                agent_role=agent.ROLE,
                category="tool",
                priority="P2",
                title=f"缺少工具: {error_msg[:50]}",
                description=f"执行任务时缺少必要工具/模块: {error_msg}",
            )
    except Exception:
        pass


async def periodic_reflection_hook(agent) -> list[dict[str, Any]]:
    """
    定期自省 (每24h触发一次):
    Agent 全面审视自己的能力和资源。
    """
    try:
        prompt = (
            f"你是{agent.DISPLAY_NAME}。进行一次全面自省:\n\n"
            f"1. **能力缺口**: 你目前最缺什么能力/工具/技能？\n"
            f"2. **资源需求**: 需要什么资源(服务器/存储/API/预算)？\n"
            f"3. **效率改进**: 哪些重复性工作可以自动化？\n"
            f"4. **人手不足**: 需要新的下属Agent吗？做什么？\n"
            f"5. **协作痛点**: 和其他首席协作有什么不顺？\n\n"
            f"对每项列出具体需求，用格式:\n"
            f"NEED|category|priority|title|description\n"
            f"如果没有需求，回复 NONE。"
        )

        response = await agent._llm_think(prompt, {})

        needs = []
        if "NEED|" in response:
            for line in response.strip().split("\n"):
                if line.startswith("NEED|"):
                    parts = line.split("|")
                    if len(parts) >= 5:
                        n = submit_need(
                            agent_role=agent.ROLE,
                            category=parts[1].strip(),
                            priority=parts[2].strip(),
                            title=parts[3].strip(),
                            description=parts[4].strip(),
                        )
                        needs.append(n)
        return needs

    except Exception:
        return []


async def compile_needs_report() -> str:
    """
    GM 调用: 整理所有首席的需求，生成汇报。
    可以发给老板审阅。
    """
    needs = get_needs_queue()
    if not needs:
        return "目前没有待处理的需求。"

    # 按优先级排序
    priority_order = {"P0": 0, "P1": 1, "P2": 2}
    sorted_needs = sorted(needs, key=lambda n: priority_order.get(n["priority"], 9))

    lines = ["# 首席需求汇总\n"]
    for n in sorted_needs:
        lines.append(
            f"- **[{n['priority']}]** {n['title']}\n"
            f"  提交人: {n['agent_role']} | 类型: {n['category']}\n"
            f"  {n['description']}\n"
        )

    return "\n".join(lines)
