"""
Guards — Permission, rate limiting, and interrupt-before-execution logic.
"""

from __future__ import annotations

from typing import Any

from src.core.state import SiliconState


# ─── Physical Action Classification ───

PHYSICAL_ACTIONS = {
    "rpa_operate",          # Shopify/Amazon RPA actions
    "send_email",           # Gmail outbound
    "send_dm",              # Platform DMs
    "create_ad",            # Ad spend
    "update_price",         # Price changes
    "create_product",       # Product listings
    "place_order",          # Purchase orders
}

AUTO_APPROVE_ACTIONS = {
    "scrape_data",          # Read-only crawling
    "analyze_data",         # Internal computation
    "generate_draft",       # Draft content generation
    "vector_search",        # Knowledge retrieval
    "internal_message",     # Inter-agent communication
}


def requires_approval(action: str) -> bool:
    """Check if an action requires L0 approval (interrupt_before)."""
    return action in PHYSICAL_ACTIONS


def is_auto_approve(action: str) -> bool:
    """Check if an action can proceed without any approval."""
    return action in AUTO_APPROVE_ACTIONS


# ─── Decision Auto-Judge ───

def auto_judge(state: SiliconState) -> str:
    """
    Auto-judge logic for Async Joint Session.
    
    Returns:
        "auto_approve" — All conditions met, proceed
        "escalate" — Serious disagreement, escalate to Adversarial Hearing
        "revise" — Minor issues, ask CGO to revise
    """
    dm = state.decision_matrix

    # All four green → auto approve
    if (
        dm.profit_pct > state_threshold_profit()
        and dm.risk_score <= state_threshold_risk()
        and dm.tech_ready
        and dm.consensus
    ):
        return "auto_approve"

    # Two or more VETOs → escalate to hearing
    vetoes = [
        role
        for role, entry in state.critique_logs.items()
        if entry.verdict == "VETO"
    ]
    if len(vetoes) >= 2:
        return "escalate"

    # Max iterations reached → escalate
    if state.iteration_count >= _max_iterations():
        return "escalate"

    return "revise"


# ─── MCP Permission Matrix ───

# Which MCP servers each role can access, and with what permissions
MCP_PERMISSIONS: dict[str, dict[str, str]] = {
    "gm": {
        "supabase": "read_write:decisions",
        "redis": "read_write",
        "feishu": "send_card,send_message",
    },
    "cgo": {
        "supabase": "read:products,suppliers",
        "playwright": "scrape",
        "redis": "read_write",
    },
    "coo": {
        "supabase": "read:all,write:decisions",
        "redis": "read_write",
        "shopify": "read:orders",
    },
    "cro": {
        "supabase": "read:policies,products",
        "playwright": "detect",
        "redis": "read_write",
        "feishu": "send_alert",
    },
    "cto": {
        "supabase": "read_write:tool_registry",
        "playwright": "debug",
        "filesystem": "full",
        "redis": "read_write",
        "feishu": "send_alert",
    },
}


def check_mcp_permission(role: str, server: str, action: str = "") -> bool:
    """Check if a role has permission to use a specific MCP server."""
    role_perms = MCP_PERMISSIONS.get(role, {})
    return server in role_perms


# ─── Internal Helpers ───

def state_threshold_profit() -> float:
    from src.config.settings import get_settings
    return get_settings().auto_approve_profit_threshold


def state_threshold_risk() -> int:
    from src.config.settings import get_settings
    return get_settings().auto_approve_risk_threshold


def _max_iterations() -> int:
    from src.config.settings import get_settings
    return get_settings().max_iteration_count
