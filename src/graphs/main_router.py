"""
Main Router — Entry point that routes L0 intent to the appropriate mode/meeting.
"""

from __future__ import annotations

from langgraph.graph import StateGraph, END

from src.core.state import SiliconState
from src.agents import GMAgent


gm = GMAgent()


# ─── Node Functions ───

async def parse_intent(state: dict) -> dict:
    """GM parses L0's natural language intent."""
    s = SiliconState(**state)
    result = await gm.parse_intent(s)
    # In a real implementation, we'd parse the JSON from the LLM response
    # For now, return the raw result for downstream routing
    return {"phase": "INTENT_PARSED"}


def route_to_mode(state: dict) -> str:
    """Route to the appropriate operating mode."""
    s = SiliconState(**state)
    return gm.route_mode(s)


async def exploration_entry(state: dict) -> dict:
    """Entry point for exploration mode — sets up state."""
    return {
        "mode": "EXPLORATION",
        "meeting_type": "EXPLORATION_CHAT",
        "phase": "EXPLORING",
    }


async def execution_entry(state: dict) -> dict:
    """Entry point for execution mode — sets up state."""
    return {
        "mode": "EXECUTION",
        "meeting_type": "ASYNC_JOINT",
        "phase": "EXECUTING",
    }


async def self_heal_entry(state: dict) -> dict:
    """Entry point for self-healing mode."""
    return {
        "mode": "EXECUTION",
        "meeting_type": "SELF_HEAL",
        "phase": "DIAGNOSING",
    }


# ─── Graph Build ───

def build_main_router() -> StateGraph:
    """Build the Main Router graph that dispatches to sub-graphs."""
    graph = StateGraph(dict)

    graph.add_node("parse_intent", parse_intent)
    graph.add_node("exploration_entry", exploration_entry)
    graph.add_node("execution_entry", execution_entry)
    graph.add_node("self_heal_entry", self_heal_entry)

    graph.set_entry_point("parse_intent")

    graph.add_conditional_edges(
        "parse_intent",
        route_to_mode,
        {
            "exploration": "exploration_entry",
            "execution": "execution_entry",
            "self_heal": "self_heal_entry",
        },
    )

    # Each entry point leads to END of this router
    # The caller will then invoke the appropriate sub-graph
    graph.add_edge("exploration_entry", END)
    graph.add_edge("execution_entry", END)
    graph.add_edge("self_heal_entry", END)

    return graph
