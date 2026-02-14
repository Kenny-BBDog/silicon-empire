"""
集体进化循环 — 全员自省 → 讨论 → CTO 执行

Flow:
  all_reflect → share_findings → evolution_meeting
    → cto_plan → approve → execute → verify

触发方式:
  - 飞书 /进化 命令
  - 定时 (每 24h)
  - 任何首席主动发起
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, END

from src.agents.l1_gm import GMAgent
from src.agents.l2_cgo import CGOAgent
from src.agents.l2_coo import COOAgent
from src.agents.l2_cro import CROAgent
from src.agents.l2_cto import CTOAgent

gm = GMAgent()
cgo = CGOAgent()
coo = COOAgent()
cro = CROAgent()
cto = CTOAgent()

ALL_CHIEFS = {"gm": gm, "cgo": cgo, "coo": coo, "cro": cro, "cto": cto}


# ─── Nodes ───

async def all_reflect(state: dict) -> dict:
    """
    各首席自省 — 扫描自己的领域，发现不足。
    并行调用每个首席的 reflect 方法。
    """
    reflections = {}

    for role, agent in ALL_CHIEFS.items():
        try:
            await agent.initialize()

            prompt = (
                f"你是{agent.DISPLAY_NAME}。进行自省：\n\n"
                f"1. 回顾最近的工作和决策\n"
                f"2. 找出 3 个最需要改进的点\n"
                f"3. 对于每个改进点：\n"
                f"   - 痛点描述 (具体场景)\n"
                f"   - 建议方案 (新Agent/新Skill/优化现有)\n"
                f"   - 预期价值\n\n"
                f"输出你真实的需求。你可以提出：\n"
                f"- 需要新的下属Agent帮你做事\n"
                f"- 需要新的Skill/工具\n"
                f"- 需要新的中台部门\n"
                f"- 需要优化记忆/数据库\n"
                f"- 需要改善和其他首席的协作方式\n"
                f"简洁、具体地表达。"
            )

            result = await agent._llm_think(prompt, {})
            reflections[role] = result
        except Exception as e:
            reflections[role] = f"自省失败: {e}"

    return {
        **state,
        "reflections": reflections,
        "phase": "reflected",
    }


async def share_findings(state: dict) -> dict:
    """
    汇总自省发现 — GM 整理各首席的发现，提炼优先议题。
    """
    reflections = state.get("reflections", {})

    await gm.initialize()

    summary_text = "\n\n".join(
        f"### {ALL_CHIEFS[r].DISPLAY_NAME}\n{content}"
        for r, content in reflections.items()
    )

    prompt = (
        f"各首席的自省结果如下:\n\n{summary_text}\n\n"
        f"作为 GM，你需要:\n"
        f"1. 汇总所有发现，去除重复\n"
        f"2. 提炼出 TOP 3-5 个最有价值的进化方向\n"
        f"3. 按优先级排序 (P0/P1/P2)\n"
        f"4. 对每个方向说明: 谁提出的、解决什么问题、预期价值\n\n"
        f"简洁输出。"
    )

    summary = await gm._llm_think(prompt, {})

    # 发送到飞书
    try:
        from src.integrations.feishu_client import get_feishu_client
        feishu = get_feishu_client()
        await feishu.send_as("system", "decision",
            f"🧬 **进化自省完成 — 发现以下改进方向:**\n\n{summary}",
            title="进化看板",
        )
    except Exception:
        pass

    return {
        **state,
        "evolution_summary": summary,
        "phase": "shared",
    }


async def evolution_meeting(state: dict) -> dict:
    """
    进化讨论 — 各首席对进化方向发表意见，投票。
    """
    summary = state.get("evolution_summary", "")
    votes = {}

    for role, agent in ALL_CHIEFS.items():
        if role == "gm":
            continue  # GM 最后总结

        try:
            await agent.initialize()
            prompt = (
                f"GM 汇总了以下进化方向:\n\n{summary}\n\n"
                f"你是{agent.DISPLAY_NAME}，请:\n"
                f"1. 对每个方向投票: 支持(+1)/中立(0)/反对(-1)\n"
                f"2. 简要说明理由\n"
                f"3. 如果你愿意牵头某个方向，说明\n"
                f"简洁回复。"
            )
            vote = await agent._llm_think(prompt, {})
            votes[role] = vote
        except Exception as e:
            votes[role] = f"投票失败: {e}"

    # GM 最终裁决
    await gm.initialize()
    vote_text = "\n\n".join(
        f"**{ALL_CHIEFS[r].DISPLAY_NAME}**: {v}" for r, v in votes.items()
    )

    prompt = (
        f"各首席投票结果:\n\n{vote_text}\n\n"
        f"原始进化方向:\n{summary}\n\n"
        f"作为 GM，做最终决定:\n"
        f"1. 本轮执行哪几个进化方向？\n"
        f"2. 按什么顺序？\n"
        f"3. 谁牵头、谁配合？\n"
        f"4. 是否需要老板审批？(重大变更需要)\n\n"
        f"输出具体的进化行动计划。"
    )

    decision = await gm._llm_think(prompt, {})

    # 发送到飞书
    try:
        from src.integrations.feishu_client import get_feishu_client
        feishu = get_feishu_client()
        await feishu.send_as("gm", "decision",
            f"🏛️ **进化会议结论:**\n\n{decision}",
            title="进化决议",
        )
    except Exception:
        pass

    return {
        **state,
        "votes": votes,
        "evolution_decision": decision,
        "phase": "decided",
    }


async def cto_plan(state: dict) -> dict:
    """CTO 根据决议制定技术执行方案。"""
    decision = state.get("evolution_decision", "")

    await cto.initialize()

    prompt = (
        f"GM 的进化决议:\n\n{decision}\n\n"
        f"你是 CTO，为每个要执行的进化方向制定技术方案:\n"
        f"1. 需要创建/修改哪些文件\n"
        f"2. 需要新建什么表/数据库\n"
        f"3. 需要部署什么新 Agent/Skill\n"
        f"4. 预估工时\n"
        f"5. 风险点\n\n"
        f"输出可执行的技术方案。"
    )

    plan = await cto._llm_think(prompt, {})

    return {
        **state,
        "technical_plan": plan,
        "phase": "planned",
    }


async def submit_approval(state: dict) -> dict:
    """发送审批卡片给老板。"""
    plan = state.get("technical_plan", "")
    decision = state.get("evolution_decision", "")

    try:
        from src.integrations.feishu_client import get_feishu_client
        feishu = get_feishu_client()
        await feishu.send_as("cto", "decision",
            f"📋 **进化方案等待审批**\n\n"
            f"## 决议\n{decision[:500]}\n\n"
            f"## 技术方案\n{plan[:500]}\n\n"
            f"请老板审批 ✅ / ❌",
            title="进化审批",
        )
    except Exception:
        pass

    return {**state, "phase": "awaiting_approval"}


# ─── Graph Build ───

def build_evolution_graph():
    """
    Build the Collective Evolution graph.

    Flow: all_reflect → share_findings → evolution_meeting
      → cto_plan → submit_approval → END (等待审批回调)
    """
    graph = StateGraph(dict)

    graph.add_node("all_reflect", all_reflect)
    graph.add_node("share_findings", share_findings)
    graph.add_node("evolution_meeting", evolution_meeting)
    graph.add_node("cto_plan", cto_plan)
    graph.add_node("submit_approval", submit_approval)

    graph.set_entry_point("all_reflect")
    graph.add_edge("all_reflect", "share_findings")
    graph.add_edge("share_findings", "evolution_meeting")
    graph.add_edge("evolution_meeting", "cto_plan")
    graph.add_edge("cto_plan", "submit_approval")
    graph.add_edge("submit_approval", END)

    return graph.compile()
