"""
Async Joint Session — Daily business approval without L0 involvement.

CGO proposes → COO/CRO/CTO review in parallel → GM aggregates → auto-judge.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, END

from src.core.state import SiliconState, CritiqueEntry
from src.core.guards import auto_judge
from src.agents import GMAgent, CGOAgent, COOAgent, CROAgent, CTOAgent


gm = GMAgent()
cgo = CGOAgent()
coo = COOAgent()
cro = CROAgent()
cto = CTOAgent()


# ─── Node Functions ───

async def cgo_propose(state: dict) -> dict:
    """CGO generates a proposal from strategic intent."""
    s = SiliconState(**state)
    result = await cgo.generate_proposal(s)
    proposal = {
        "version": len(s.proposal_buffer) + 1,
        "author": "CGO",
        "content": result.get("proposal", ""),
    }
    return {"proposal_buffer": list(s.proposal_buffer) + [proposal]}


async def coo_review(state: dict) -> dict:
    """COO reviews cost structure."""
    s = SiliconState(**state)
    result = await coo.review_proposal(s)
    critiques = dict(s.critique_logs)
    critiques["coo"] = CritiqueEntry(**result.get("critique_entry", {}))
    return {"critique_logs": critiques}


async def cro_review(state: dict) -> dict:
    """CRO reviews compliance."""
    s = SiliconState(**state)
    result = await cro.review_proposal(s)
    critiques = dict(s.critique_logs)
    critiques["cro"] = CritiqueEntry(**result.get("critique_entry", {}))
    return {"critique_logs": critiques}


async def cto_review(state: dict) -> dict:
    """CTO reviews tech feasibility."""
    s = SiliconState(**state)
    result = await cto.review_proposal(s)
    critiques = dict(s.critique_logs)
    critiques["cto"] = CritiqueEntry(**result.get("critique_entry", {}))
    return {"critique_logs": critiques}


async def gm_aggregate(state: dict) -> dict:
    """GM aggregates all reviews into decision matrix."""
    s = SiliconState(**state)
    result = await gm.aggregate_reviews(s)
    return {"phase": "AGGREGATED"}


def gm_judge(state: dict) -> str:
    """Auto-judge: approve, revise, or escalate."""
    s = SiliconState(**state)
    return auto_judge(s)


async def execute_approved(state: dict) -> dict:
    """Handle auto-approved decision."""
    return {
        "l0_verdict": "AUTO_APPROVED",
        "phase": "EXECUTION",
    }


async def request_revision(state: dict) -> dict:
    """Request CGO to revise the proposal."""
    s = SiliconState(**state)
    return {
        "iteration_count": s.iteration_count + 1,
        "phase": "REVISING",
    }


async def escalate_to_hearing(state: dict) -> dict:
    """Escalate to adversarial hearing."""
    return {
        "meeting_type": "ADVERSARIAL_HEARING",
        "phase": "ESCALATED",
    }


# ─── Graph Build ───

def build_async_session_graph() -> StateGraph:
    """Build the Async Joint Session state graph."""
    graph = StateGraph(dict)

    # Nodes
    graph.add_node("cgo_propose", cgo_propose)
    graph.add_node("coo_review", coo_review)
    graph.add_node("cro_review", cro_review)
    graph.add_node("cto_review", cto_review)
    graph.add_node("gm_aggregate", gm_aggregate)
    graph.add_node("execute_approved", execute_approved)
    graph.add_node("request_revision", request_revision)
    graph.add_node("escalate_to_hearing", escalate_to_hearing)

    # Entry
    graph.set_entry_point("cgo_propose")

    # CGO → parallel reviews (simulated as sequential for determinism)
    graph.add_edge("cgo_propose", "coo_review")
    graph.add_edge("coo_review", "cro_review")
    graph.add_edge("cro_review", "cto_review")
    graph.add_edge("cto_review", "gm_aggregate")

    # GM → conditional judge
    graph.add_conditional_edges(
        "gm_aggregate",
        gm_judge,
        {
            "auto_approve": "execute_approved",
            "revise": "request_revision",
            "escalate": "escalate_to_hearing",
        },
    )

    # Revision loop back to CGO
    graph.add_edge("request_revision", "cgo_propose")

    # Terminal nodes
    graph.add_edge("execute_approved", END)
    graph.add_edge("escalate_to_hearing", END)

    return graph
