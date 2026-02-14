"""
Exploration Mode — GroupChat SubGraph.

Four C-Suite agents engage in free-form, multi-round discussions.
GM moderates and checks for convergence. Max 5 rounds.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, END

from src.core.state import SiliconState
from src.agents import GMAgent, CGOAgent, COOAgent, CROAgent, CTOAgent


# ─── Agent singletons ───
gm = GMAgent()
cgo = CGOAgent()
coo = COOAgent()
cro = CROAgent()
cto = CTOAgent()


# ─── Node Functions ───

async def cgo_speak(state: dict) -> dict:
    """CGO shares opportunity insights."""
    s = SiliconState(**state)
    result = await cgo.debate(s, round_num=s.iteration_count * 4 + 1)
    transcript = list(s.meeting_transcript) + [{
        "round": s.iteration_count + 1,
        "speaker": "CGO",
        "content": result["content"],
    }]
    return {"meeting_transcript": transcript}


async def cro_challenge(state: dict) -> dict:
    """CRO raises risk concerns."""
    s = SiliconState(**state)
    result = await cro.debate(s, round_num=s.iteration_count * 4 + 2)
    transcript = list(s.meeting_transcript) + [{
        "round": s.iteration_count + 1,
        "speaker": "CRO",
        "content": result["content"],
    }]
    return {"meeting_transcript": transcript}


async def coo_calculate(state: dict) -> dict:
    """COO adds data-driven perspective."""
    s = SiliconState(**state)
    result = await coo.debate(s, round_num=s.iteration_count * 4 + 3)
    transcript = list(s.meeting_transcript) + [{
        "round": s.iteration_count + 1,
        "speaker": "COO",
        "content": result["content"],
    }]
    return {"meeting_transcript": transcript}


async def cto_evaluate(state: dict) -> dict:
    """CTO assesses technical feasibility."""
    s = SiliconState(**state)
    result = await cto.debate(s, round_num=s.iteration_count * 4 + 4)
    transcript = list(s.meeting_transcript) + [{
        "round": s.iteration_count + 1,
        "speaker": "CTO",
        "content": result["content"],
    }]
    return {
        "meeting_transcript": transcript,
        "iteration_count": s.iteration_count + 1,
    }


async def gm_moderate(state: dict) -> dict:
    """GM checks if discussion has converged."""
    s = SiliconState(**state)
    convergence = await gm.check_convergence(s)
    return {"phase": convergence}  # "converged" or "continue"


async def draft_proposal(state: dict) -> dict:
    """GM synthesizes discussion into a formal proposal."""
    s = SiliconState(**state)
    result = await gm.summarize_hearing(s)
    proposal = {
        "version": len(s.proposal_buffer) + 1,
        "author": "GM (Exploration Synthesis)",
        "content": result.get("hearing_summary", ""),
    }
    return {
        "proposal_buffer": list(s.proposal_buffer) + [proposal],
        "phase": "PROPOSAL_READY",
    }


# ─── Routing ───

def should_continue(state: dict) -> str:
    """Determine if discussion should continue or conclude."""
    s = SiliconState(**state)
    if s.iteration_count >= 5:
        return "force_conclude"
    if s.phase == "converged":
        return "conclude"
    return "continue"


# ─── Graph Build ───

def build_exploration_graph() -> StateGraph:
    """Build the Exploration Mode state graph."""
    graph = StateGraph(dict)

    # Nodes
    graph.add_node("cgo_speak", cgo_speak)
    graph.add_node("cro_challenge", cro_challenge)
    graph.add_node("coo_calculate", coo_calculate)
    graph.add_node("cto_evaluate", cto_evaluate)
    graph.add_node("gm_moderate", gm_moderate)
    graph.add_node("draft_proposal", draft_proposal)

    # Edges: Sequential discussion round
    graph.set_entry_point("cgo_speak")
    graph.add_edge("cgo_speak", "cro_challenge")
    graph.add_edge("cro_challenge", "coo_calculate")
    graph.add_edge("coo_calculate", "cto_evaluate")
    graph.add_edge("cto_evaluate", "gm_moderate")

    # Conditional: continue discussion or conclude
    graph.add_conditional_edges(
        "gm_moderate",
        should_continue,
        {
            "continue": "cgo_speak",
            "conclude": "draft_proposal",
            "force_conclude": "draft_proposal",
        },
    )

    graph.add_edge("draft_proposal", END)

    return graph
