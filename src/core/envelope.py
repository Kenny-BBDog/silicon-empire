"""
Dual-Layer Communication Protocol.

Header (JSON) — for routing & state management.
Body (Markdown) — for LLM reasoning & human observation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class EnvelopeHeader(BaseModel):
    """Machine-readable routing metadata."""

    trace_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    from_node: str                    # e.g. "L2_CGO", "L3_Intel"
    to_node: str                      # e.g. "L3_Creative", "L1_GM"
    intent: str                       # e.g. "MARKET_ANALYSIS", "COST_CHECK"
    priority: str = "NORMAL"          # P0 (urgent) | HIGH | NORMAL | LOW
    context_snapshot_id: str = ""     # Redis key for current memory context
    expect_output_schema: str = ""   # Expected response schema name
    status: str = "PENDING"          # PENDING | IN_PROGRESS | DONE | ERROR


class Envelope(BaseModel):
    """
    The complete communication unit between agents.
    
    - header: JSON for n8n routing & programmatic parsing
    - body: Markdown for LLM reasoning & Feishu display
    """

    header: EnvelopeHeader
    body: str  # Markdown content with ## Context, ## Strategy, ## Constraints

    def to_routing_dict(self) -> dict[str, Any]:
        """Export header as dict for Redis/n8n routing."""
        return self.header.model_dump()

    def to_display(self) -> str:
        """Format for human-readable display (e.g., Feishu channel)."""
        meta = f"📨 **{self.header.from_node}** → **{self.header.to_node}**"
        meta += f" | Intent: `{self.header.intent}` | Priority: `{self.header.priority}`"
        return f"{meta}\n\n---\n\n{self.body}"

    def to_llm_context(self) -> str:
        """Format for feeding into an LLM as context."""
        return (
            f"[From: {self.header.from_node} | Intent: {self.header.intent} | "
            f"Priority: {self.header.priority}]\n\n{self.body}"
        )


def create_envelope(
    from_node: str,
    to_node: str,
    intent: str,
    body: str,
    priority: str = "NORMAL",
    trace_id: str | None = None,
) -> Envelope:
    """Factory function to create a new Envelope."""
    return Envelope(
        header=EnvelopeHeader(
            trace_id=trace_id or str(uuid.uuid4()),
            from_node=from_node,
            to_node=to_node,
            intent=intent,
            priority=priority,
        ),
        body=body,
    )
