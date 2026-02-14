"""
Holiday ChatRoom — 全员自由讨论模式 (放假/研讨/头脑风暴)

设计理念：
- 不是"狼人杀"轮流说话，而是真正的自由讨论
- GM 作为隐形主持人，每轮判断"谁最想说话"
- 同一个人可以连续发言多次（比如 CGO 和 CRO 吵起来了）
- Agent 可以选择"没什么补充"来 pass
- 没有层级，GM 也只是普通参与者
- 每个 Agent 看到完整的聊天记录（不只是上一位的话）

对比正式会议：
- 正式会议 → 有层级、有发言顺序、GM 有裁决权
- 放假模式 → 无层级、动态发言、纯粹交流
"""

from __future__ import annotations

import random
from typing import Any
from datetime import datetime, timezone

from langgraph.graph import StateGraph, END

from src.agents import GMAgent, CGOAgent, COOAgent, CROAgent, CTOAgent
from src.config.models import get_llm
from src.core.personal_memory import MemoryEntry
from langchain_core.messages import SystemMessage, HumanMessage


# ─── 全员花名册 ───

ALL_AGENTS = {
    "gm": GMAgent(),
    "cgo": CGOAgent(),
    "coo": COOAgent(),
    "cro": CROAgent(),
    "cto": CTOAgent(),
    # 未来扩展 L3/L4:
    # "l3_hunter": HunterAgent(),
    # "l3_copywriter": CopywriterAgent(),
    # "l4_autolab": AutoLabAgent(),
}


# ─── Node Functions ───

async def start_holiday(state: dict) -> dict:
    """GM 宣布放假，所有人放下工作。"""
    gm = ALL_AGENTS["gm"]
    await gm.initialize()

    topic = state.get("topic", "")
    names = "、".join(a.DISPLAY_NAME for a in ALL_AGENTS.values())

    announcement = f"🏖️ **放假啦！** 大家放下手头的工作，自由聊天时间到。\n参与者: {names}"
    if topic:
        announcement += f"\n今天的话题: **{topic}**\n想到什么就说什么，不用举手。"
    else:
        announcement += "\n没有特定话题，随便聊聊。想到什么就说什么。"

    await gm.memory.think("发起了一次团队放假聊天活动", importance=5)

    return {
        "meeting_transcript": [{
            "round": 0,
            "speaker": "系统",
            "content": announcement,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }],
        "turn_count": 0,
        "consecutive_passes": 0,
        "phase": "chatting",
    }


async def pick_next_speaker(state: dict) -> dict:
    """
    核心: 动态选择下一个发言者。
    
    不用固定顺序。GM (作为隐形导演) 读完整 transcript，
    判断谁最可能有话要说。考虑因素:
    - 谁跟当前话题最相关
    - 谁已经很久没说话了
    - 谁被点名/提到了
    - 自然的对话节奏（刚说完话的人不太可能立刻又说）
    """
    transcript = state.get("meeting_transcript", [])
    topic = state.get("topic", "")
    turn_count = state.get("turn_count", 0)

    # 统计每个人的发言情况
    all_roles = list(ALL_AGENTS.keys())
    speak_counts = {role: 0 for role in all_roles}
    last_spoke = {role: -999 for role in all_roles}

    for i, entry in enumerate(transcript):
        speaker_role = entry.get("role", "")
        if speaker_role in speak_counts:
            speak_counts[speaker_role] += 1
            last_spoke[speaker_role] = i

    # 用 LLM 判断谁最应该发言
    recent_transcript = "\n".join(
        f"**{t['speaker']}**: {t['content']}"
        for t in transcript[-8:]  # 最近 8 条
    )

    speak_stats = "\n".join(
        f"- {ALL_AGENTS[role].DISPLAY_NAME}: 已说 {speak_counts[role]} 次, "
        f"上次发言在第 {last_spoke[role]} 条"
        for role in all_roles
    )

    prompt = (
        f"你是一个自由讨论的隐形导播。根据对话内容，判断下一个最自然的发言者。\n\n"
        f"## 话题\n{topic or '自由闲聊'}\n\n"
        f"## 最近对话\n{recent_transcript}\n\n"
        f"## 参与者发言统计\n{speak_stats}\n\n"
        f"## 规则\n"
        f"- 选择跟当前话题最相关、最可能想接话的人\n"
        f"- 被点名或被提到的人优先\n"
        f"- 太久没说话的人适当照顾\n"
        f"- 刚刚连续说了 2 次的人暂时让一让\n"
        f"- 如果对话已经充分，所有人都没什么新观点了，返回 NOBODY\n\n"
        f"只返回一个角色 ID: {', '.join(all_roles)}，或者 NOBODY。"
    )

    llm = get_llm("gm", temperature=0.5)
    response = await llm.ainvoke([
        SystemMessage(content="你是对话导播，只返回一个角色ID或NOBODY，不解释。"),
        HumanMessage(content=prompt),
    ])

    chosen = response.content.strip().lower()

    # 容错: 如果 LLM 返回了奇怪的东西
    if chosen not in all_roles and chosen != "nobody":
        # 从未发言或发言最少的人中随机选
        min_count = min(speak_counts.values())
        candidates = [r for r, c in speak_counts.items() if c == min_count]
        # 排除刚刚说话的人
        if transcript:
            last_role = transcript[-1].get("role", "")
            candidates = [c for c in candidates if c != last_role] or candidates
        chosen = random.choice(candidates)

    return {"next_speaker": chosen}


async def agent_speak(state: dict) -> dict:
    """让被选中的 Agent 自由发言。"""
    speaker_role = state.get("next_speaker", "")

    if speaker_role == "nobody" or speaker_role not in ALL_AGENTS:
        return {
            "consecutive_passes": state.get("consecutive_passes", 0) + 1,
        }

    agent = ALL_AGENTS[speaker_role]
    topic = state.get("topic", "")
    transcript = state.get("meeting_transcript", [])

    result = await agent.chat_freely(topic, transcript)

    # 检查是否 pass
    content = result.get("content", "")
    is_pass = any(phrase in content for phrase in [
        "没什么补充", "没什么要说", "同意", "pass", "我先听着",
        "不补充了", "暂时没有",
    ])

    # 所有人都看到了这条消息后，更新对发言者的印象
    for role, other_agent in ALL_AGENTS.items():
        if role != speaker_role and not is_pass:
            try:
                await other_agent.memory.update_impression(
                    agent.DISPLAY_NAME,
                    f"在闲聊中说: {content[:100]}",
                    tone="positive" if any(w in content for w in ["好主意", "同意", "赞"]) else "neutral",
                )
            except Exception:
                pass

    new_entry = {
        "round": state.get("turn_count", 0) + 1,
        "speaker": result["speaker"],
        "role": speaker_role,
        "content": content,
        "mood": result.get("mood", "neutral"),
        "is_pass": is_pass,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "meeting_transcript": list(transcript) + [new_entry],
        "turn_count": state.get("turn_count", 0) + 1,
        "consecutive_passes": (state.get("consecutive_passes", 0) + 1) if is_pass else 0,
    }


async def end_holiday(state: dict) -> dict:
    """
    放假结束 — 所有 Agent 自我反思，归档记忆。
    类似人"睡前回顾今天发生了什么"。
    """
    reflections = []

    for role, agent in ALL_AGENTS.items():
        try:
            thoughts = await agent.memory.reflect()
            if thoughts:
                await agent.memory.remember(MemoryEntry(
                    content=f"放假聊天反思:\n{thoughts}",
                    memory_type="reflection",
                    importance=6,
                    related_agents=[r for r in ALL_AGENTS if r != role],
                ))
                reflections.append({
                    "agent": agent.DISPLAY_NAME,
                    "reflection": thoughts[:200],
                })
            await agent.memory.archive_working_memory()
        except Exception:
            pass

    transcript = state.get("meeting_transcript", [])
    transcript.append({
        "round": state.get("turn_count", 0) + 1,
        "speaker": "系统",
        "content": f"🌙 放假结束。{len(reflections)} 位员工完成了自我反思，重要记忆已归档。",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "meeting_transcript": transcript,
        "reflections": reflections,
        "phase": "holiday_ended",
    }


# ─── Routing ───

def should_continue(state: dict) -> str:
    """判断聊天是否继续。"""
    turn_count = state.get("turn_count", 0)
    max_turns = state.get("max_turns", 15)             # 最多 15 个发言轮次
    consecutive_passes = state.get("consecutive_passes", 0)
    next_speaker = state.get("next_speaker", "")

    # 导播说 NOBODY 了 → 大家都聊完了
    if next_speaker == "nobody":
        return "end"

    # 连续 3 个人 pass → 没人想说了
    if consecutive_passes >= 3:
        return "end"

    # 超过最大轮次
    if turn_count >= max_turns:
        return "end"

    return "speak"


# ─── Graph Build ───

def build_holiday_graph() -> StateGraph:
    """
    Build the Holiday ChatRoom graph.
    
    Flow: start → [pick_next_speaker → agent_speak] × dynamic → end
    
    核心区别 vs 正式会议:
    - 正式会议: 固定顺序 (CGO→COO→CRO→CTO), 有层级
    - 放假模式: 动态选人, 无层级, 可连续发言
    """
    graph = StateGraph(dict)

    # Nodes
    graph.add_node("start_holiday", start_holiday)
    graph.add_node("pick_next_speaker", pick_next_speaker)
    graph.add_node("agent_speak", agent_speak)
    graph.add_node("end_holiday", end_holiday)

    # Entry
    graph.set_entry_point("start_holiday")
    graph.add_edge("start_holiday", "pick_next_speaker")

    # 导播选人后 → 该人发言
    graph.add_edge("pick_next_speaker", "agent_speak")

    # 发言后 → 继续选人 或 结束
    graph.add_conditional_edges(
        "agent_speak",
        should_continue,
        {
            "speak": "pick_next_speaker",
            "end": "end_holiday",
        },
    )

    graph.add_edge("end_holiday", END)

    return graph
