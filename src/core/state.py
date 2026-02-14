"""
Silicon-Empire Unified State Definition.

This is the single source of truth for all data flowing through the system.
Every LangGraph node reads from and writes to this state.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


def _uuid() -> str:
    return str(uuid.uuid4())


class CritiqueEntry(BaseModel):
    """A single C-Suite member's review output."""

    verdict: str = "PENDING"  # APPROVE | REJECT | VETO | PENDING
    analysis: str = ""        # Markdown analysis body
    data: dict[str, Any] = Field(default_factory=dict)  # Structured metrics


class DecisionMatrix(BaseModel):
    """Aggregated decision parameters computed by GM."""

    profit_pct: float = 0.0
    risk_score: int = 0        # 1-5, where 1=lowest
    tech_ready: bool = False
    consensus: bool = False
    summary: str = ""


class SiliconState(BaseModel):
    """
    The unified state graph object for Silicon-Empire.
    All agents have controlled read/write access to this state.
    """

    # ─── Metadata ───
    trace_id: str = Field(default_factory=_uuid)
    mode: str = "EXECUTION"          # EXPLORATION | EXECUTION
    phase: str = "INIT"              # Current state-machine phase
    meeting_type: str = ""           # ASYNC_JOINT | ADVERSARIAL_HEARING | EXPLORATION_CHAT

    # ─── Intent Layer ───
    strategic_intent: str = ""       # L0's original goal (natural language)
    intent_category: str = ""        # NEW_CATEGORY | PRODUCT_LAUNCH | SOURCING | TECH_FIX

    # ─── Proposal Layer ───
    proposal_buffer: list[dict[str, Any]] = Field(default_factory=list)
    # Each entry: {"version": 1, "author": "CGO", "content": "...", "timestamp": "..."}

    # ─── Critique Layer ───
    critique_logs: dict[str, CritiqueEntry] = Field(
        default_factory=lambda: {
            "coo": CritiqueEntry(),
            "cro": CritiqueEntry(),
            "cto": CritiqueEntry(),
        }
    )

    # ─── Decision Layer ───
    decision_matrix: DecisionMatrix = Field(default_factory=DecisionMatrix)
    l0_verdict: str = "PENDING"  # PENDING | APPROVED | REJECTED | REVISE | AUTO_APPROVED

    # ─── Execution Layer ───
    execution_plan: list[dict[str, Any]] = Field(default_factory=list)
    execution_results: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    # Each artifact: {"type": "image|copy|report", "url": "...", "metadata": {...}}

    # ─── Meeting Transcript ───
    messages: Annotated[list, add_messages] = Field(default_factory=list)
    meeting_transcript: list[dict[str, Any]] = Field(default_factory=list)
    # Each entry: {"round": 1, "speaker": "CGO", "content": "...", "timestamp": "..."}

    # ─── System Layer ───
    checkpoint_id: str = ""
    error_log: dict[str, Any] | None = None
    iteration_count: int = 0

    class Config:
        arbitrary_types_allowed = True
