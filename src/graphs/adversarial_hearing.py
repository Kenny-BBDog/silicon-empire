"""
Adversarial Hearing — Round-robin debate for major decisions.

Round 1 (CGO): Attack — opportunity report
Round 2 (CRO): Defend — point-by-point refutation
Round 3 (COO): Arbitrate — P&L model
Round 4 (CTO): Tech assess — feasibility ruling
→ GM summarize → L0 decision via Feishu card
"""

from __future__ import annotations

from langgraph.graph import StateGraph, END

from src.core.state import SiliconState
from src.agents import GMAgent, CGOAgent, COOAgent, CROAgent, CTOAgent


gm = GMAgent()
cgo = CGOAgent()
coo = COOAgent()
cro = CROAgent()
cto = CTOAgent()


# ─── Node Functions ───

async def open_hearing(state: dict) -> dict:
    """GM announces the hearing topic."""
    return {
        "meeting_type": "ADVERSARIAL_HEARING",
        "phase": "HEARING_OPENED",
        "meeting_transcript": [],
    }


async def round_1_cgo(state: dict) -> dict:
    """Round 1: CGO presents the opportunity."""
    s = SiliconState(**state)
    result = await cgo.debate(s, round_num=1)
    return {
        "meeting_transcript": list(s.meeting_transcript) + [result],
    }


async def round_2_cro(state: dict) -> dict:
    """Round 2: CRO refutes CGO point by point."""
    s = SiliconState(**state)
    result = await cro.debate(s, round_num=2)
    return {
        "meeting_transcript": list(s.meeting_transcript) + [result],
    }


async def round_3_coo(state: dict) -> dict:
    """Round 3: COO provides P&L analysis."""
    s = SiliconState(**state)
    result = await coo.debate(s, round_num=3)
    return {
        "meeting_transcript": list(s.meeting_transcript) + [result],
    }


async def round_4_cto(state: dict) -> dict:
    """Round 4: CTO assesses technical feasibility."""
    s = SiliconState(**state)
    result = await cto.debate(s, round_num=4)
    return {
        "meeting_transcript": list(s.meeting_transcript) + [result],
    }


async def gm_summarize(state: dict) -> dict:
    """GM summarizes all four rounds into a decision card."""
    s = SiliconState(**state)
    result = await gm.summarize_hearing(s)
    return {
        "phase": "AWAITING_L0",
        # In production, this triggers Feishu card push
        "artifacts": list(s.artifacts) + [{
            "type": "hearing_summary",
            "content": result.get("hearing_summary", ""),
        }],
    }


async def l0_decision_node(state: dict) -> dict:
    """
    L0 decision checkpoint.
    In production, this is an interrupt_before node that waits for Feishu callback.
    For CLI testing, reads from stdin.
    """
    # This node will be configured with interrupt_before in the compiled graph
    return {"phase": "L0_DECIDED"}


def route_l0_verdict(state: dict) -> str:
    """Route based on L0's verdict."""
    verdict = state.get("l0_verdict", "PENDING")
    if verdict == "APPROVED":
        return "approved"
    elif verdict == "REJECTED":
        return "rejected"
    elif verdict == "REVISE":
        return "more_debate"
    else:
        return "conservative"


async def approved_handler(state: dict) -> dict:
    return {"phase": "APPROVED_EXECUTING", "l0_verdict": "APPROVED"}


async def conservative_handler(state: dict) -> dict:
    return {"phase": "CONSERVATIVE_EXECUTING", "l0_verdict": "APPROVED"}


async def rejected_handler(state: dict) -> dict:
    return {"phase": "REJECTED_ARCHIVED", "l0_verdict": "REJECTED"}


# ─── Graph Build ───

def build_adversarial_hearing_graph() -> StateGraph:
    """Build the Adversarial Hearing state graph."""
    graph = StateGraph(dict)

    # Nodes
    graph.add_node("open_hearing", open_hearing)
    graph.add_node("round_1_cgo", round_1_cgo)
    graph.add_node("round_2_cro", round_2_cro)
    graph.add_node("round_3_coo", round_3_coo)
    graph.add_node("round_4_cto", round_4_cto)
    graph.add_node("gm_summarize", gm_summarize)
    graph.add_node("l0_decision", l0_decision_node)
    graph.add_node("approved", approved_handler)
    graph.add_node("conservative", conservative_handler)
    graph.add_node("rejected", rejected_handler)

    # Edges: Linear debate flow
    graph.set_entry_point("open_hearing")
    graph.add_edge("open_hearing", "round_1_cgo")
    graph.add_edge("round_1_cgo", "round_2_cro")
    graph.add_edge("round_2_cro", "round_3_coo")
    graph.add_edge("round_3_coo", "round_4_cto")
    graph.add_edge("round_4_cto", "gm_summarize")
    graph.add_edge("gm_summarize", "l0_decision")

    # L0 conditional routing
    graph.add_conditional_edges(
        "l0_decision",
        route_l0_verdict,
        {
            "approved": "approved",
            "conservative": "conservative",
            "rejected": "rejected",
            "more_debate": "round_1_cgo",  # New round of debate
        },
    )

    # Terminal nodes
    graph.add_edge("approved", END)
    graph.add_edge("conservative", END)
    graph.add_edge("rejected", END)

    return graph
