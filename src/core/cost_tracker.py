"""
Cost Tracker — monitors per-session and per-agent token usage.

Logs usage to Redis for real-time monitoring and to Supabase for long-term analytics.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from src.config.settings import get_settings


class CostTracker:
    """Track token consumption and estimated cost across agents."""

    # Approximate cost per 1M tokens (input/output) via OpenRouter
    PRICING = {
        "openai/gpt-4o": {"input": 2.50, "output": 10.00},
        "anthropic/claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
        "google/gemini-flash-1.5": {"input": 0.075, "output": 0.30},
    }

    def __init__(self) -> None:
        self._session_usage: dict[str, dict[str, int]] = {}
        # { "cgo": {"input_tokens": 1500, "output_tokens": 300, "calls": 5} }

    def record(
        self,
        agent: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> dict[str, Any]:
        """Record a single LLM call's token usage. Returns cost info."""
        if agent not in self._session_usage:
            self._session_usage[agent] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "calls": 0,
                "cost_usd": 0.0,
            }

        pricing = self.PRICING.get(model, {"input": 5.0, "output": 15.0})
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

        entry = self._session_usage[agent]
        entry["input_tokens"] += input_tokens
        entry["output_tokens"] += output_tokens
        entry["calls"] += 1
        entry["cost_usd"] += cost

        return {
            "agent": agent,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost, 6),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_session_summary(self) -> dict[str, Any]:
        """Get cost summary for the current session."""
        total_cost = sum(a.get("cost_usd", 0) for a in self._session_usage.values())
        total_tokens = sum(
            a.get("input_tokens", 0) + a.get("output_tokens", 0)
            for a in self._session_usage.values()
        )
        return {
            "per_agent": self._session_usage,
            "total_cost_usd": round(total_cost, 4),
            "total_tokens": total_tokens,
            "budget_remaining": get_settings().token_budget_per_session - total_tokens,
        }

    def is_over_budget(self) -> bool:
        """Check if session has exceeded token budget."""
        total = sum(
            a.get("input_tokens", 0) + a.get("output_tokens", 0)
            for a in self._session_usage.values()
        )
        return total > get_settings().token_budget_per_session

    def reset(self) -> None:
        """Reset session counters."""
        self._session_usage.clear()

    def to_json(self) -> str:
        """Serialize for Redis storage."""
        return json.dumps(self._session_usage, default=str)
