"""
Memory Distiller — 记忆蒸馏。

Agent 每天产生大量碎片记忆 (scratchpad thoughts)。
蒸馏器定期把它们压缩成精华认知，避免记忆爆炸。

流程:
1. 读取 Agent 最近的所有 scratchpad
2. LLM 总结成 3-5 条精华洞察
3. 精华写入长期记忆 + 共享到知识库
4. 清空已蒸馏的 scratchpad
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("distiller")


async def distill_agent_memory(agent) -> list[str]:
    """
    蒸馏一个 Agent 的短期记忆。

    Returns: 提炼出的洞察列表
    """
    await agent.initialize()

    # 读取短期记忆
    thoughts = await agent._memory.get_thoughts(limit=50)
    if len(thoughts) < 5:
        return []  # 不够多，不需要蒸馏

    thought_text = "\n".join(
        f"- [{t.get('timestamp', '')[:16]}] {t.get('thought', '')}"
        for t in thoughts
    )

    prompt = (
        f"以下是你最近的 {len(thoughts)} 条工作笔记:\n\n"
        f"{thought_text}\n\n"
        f"请蒸馏出最有价值的 3-5 条精华洞察:\n"
        f"- 重复出现的模式/趋势\n"
        f"- 犯过的错误和教训\n"
        f"- 发现的优化机会\n"
        f"- 对其他团队有价值的信息\n\n"
        f"每条用 INSIGHT: 开头"
    )

    response = await agent._llm_think(prompt, {})

    # 解析洞察
    insights = []
    for line in response.split("\n"):
        line = line.strip()
        if line.startswith("INSIGHT:"):
            insight = line.replace("INSIGHT:", "").strip()
            if insight:
                insights.append(insight)

    # 写入长期记忆
    from src.core.personal_memory import MemoryEntry
    for insight in insights:
        await agent._memory.remember(MemoryEntry(
            content=insight,
            memory_type="insight",
            importance=8,
        ))

    # 写入共享知识库
    try:
        from src.core.knowledge_base import get_knowledge_base
        kb = await get_knowledge_base()
        for insight in insights:
            await kb.learn(
                category="lesson",
                title=f"{agent.DISPLAY_NAME} 的工作洞察",
                content=insight,
                source_agent=agent.ROLE,
                confidence=0.7,
            )
    except Exception:
        pass

    logger.info(f"Distilled {len(insights)} insights for {agent.ROLE}")
    return insights


async def distill_all_agents():
    """蒸馏所有 Agent 的记忆 (调度器每日触发)。"""
    try:
        from src.agents import get_all_chiefs
        for agent in get_all_chiefs():
            try:
                await distill_agent_memory(agent)
            except Exception as e:
                logger.error(f"Distill failed for {agent.ROLE}: {e}")
    except Exception as e:
        logger.error(f"distill_all_agents failed: {e}")
