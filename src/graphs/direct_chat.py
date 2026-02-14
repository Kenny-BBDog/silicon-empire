"""
1:1 Direct Chat — 老板和任意首席的自由对话。

特点:
- 不触发任何工作流/任务
- Agent 用自己的人格 prompt + 个人记忆回复
- 对话历史存入记忆系统
- 纯聊天，只有明确说"去做"才触发执行
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage

from src.config.models import get_llm


# ─── Agent Instances (lazy init) ───

_agents: dict[str, Any] = {}


def _get_agent(role: str):
    """Lazy-load agent instance."""
    if role not in _agents:
        if role == "gm":
            from src.agents.l1_gm import GMAgent
            _agents[role] = GMAgent()
        elif role == "cgo":
            from src.agents.l2_cgo import CGOAgent
            _agents[role] = CGOAgent()
        elif role == "coo":
            from src.agents.l2_coo import COOAgent
            _agents[role] = COOAgent()
        elif role == "cro":
            from src.agents.l2_cro import CROAgent
            _agents[role] = CROAgent()
        elif role == "cto":
            from src.agents.l2_cto import CTOAgent
            _agents[role] = CTOAgent()
        else:
            return None
    return _agents.get(role)


# ─── Chat History (in-memory, per chat_id) ───

_chat_history: dict[str, list[dict]] = {}
MAX_HISTORY = 20


def _get_history(chat_id: str, role: str) -> list[dict]:
    key = f"{chat_id}:{role}"
    return _chat_history.setdefault(key, [])


def _add_to_history(chat_id: str, role: str, user_msg: str, bot_msg: str):
    key = f"{chat_id}:{role}"
    history = _chat_history.setdefault(key, [])
    history.append({"user": user_msg, "bot": bot_msg})
    if len(history) > MAX_HISTORY:
        _chat_history[key] = history[-MAX_HISTORY:]


# ─── Main Chat Function ───

async def chat_with_agent(role: str, user_text: str, chat_id: str = "") -> str:
    """
    和指定首席 1:1 对话。

    Args:
        role: 首席角色 (gm/cgo/coo/cro/cto)
        user_text: 用户消息
        chat_id: 飞书 chat ID (用于维护对话历史)

    Returns:
        Agent 的回复
    """
    agent = _get_agent(role)
    if not agent:
        return f"未找到角色 {role} 的 Agent。"

    try:
        await agent.initialize()
    except Exception:
        pass

    # Build system prompt with personality + memory
    system_prompt = agent._prompt if hasattr(agent, "_prompt") else ""

    # Add memory context
    memory_ctx = ""
    try:
        memory_ctx = await agent._memory.build_memory_context()
    except Exception:
        pass

    # Add chat history context
    history = _get_history(chat_id, role)
    history_text = ""
    if history:
        recent = history[-5:]  # Last 5 exchanges
        history_text = "\n\n## 最近对话\n"
        for h in recent:
            history_text += f"老板: {h['user']}\n你: {h['bot']}\n\n"

    # Chat mode instruction
    chat_instruction = (
        "\n\n## 当前模式: 自由对话\n"
        "你正在和老板聊天。这不是正式任务，不需要执行任何操作。\n"
        "像一个有经验的高管那样对话 — 分享见解、讨论方案、提出建议。\n"
        "如果你觉得某个想法值得执行，可以主动说"这个方案我可以去落实，需要我执行吗？"\n"
        "但不要自作主张去做，等老板确认。\n"
        "保持简洁，像聊天一样回复，不要写长篇报告。"
    )

    full_system = system_prompt + memory_ctx + history_text + chat_instruction

    # Call LLM
    llm = get_llm(agent.LLM_ROLE, temperature=0.8)
    messages = [
        SystemMessage(content=full_system),
        HumanMessage(content=user_text),
    ]

    response = await llm.ainvoke(messages)
    reply = response.content

    # Save to history
    _add_to_history(chat_id, role, user_text, reply)

    # Save to agent memory
    try:
        await agent._memory.think(
            f"和老板聊天: {user_text[:100]} → {reply[:100]}",
            importance=3,
        )
    except Exception:
        pass

    return reply
