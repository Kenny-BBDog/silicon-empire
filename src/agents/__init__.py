"""Silicon-Empire Agents package."""

from src.agents.base import BaseAgent
from src.agents.l1_gm import GMAgent
from src.agents.l2_cgo import CGOAgent
from src.agents.l2_coo import COOAgent
from src.agents.l2_cro import CROAgent
from src.agents.l2_cto import CTOAgent

__all__ = [
    "BaseAgent",
    "GMAgent",
    "CGOAgent",
    "COOAgent",
    "CROAgent",
    "CTOAgent",
    "get_agent_by_role",
    "get_all_chiefs",
]

# ─── Agent Registry ───

_AGENT_MAP: dict[str, BaseAgent] | None = None


def _init_map() -> dict[str, BaseAgent]:
    global _AGENT_MAP
    if _AGENT_MAP is None:
        _AGENT_MAP = {
            "gm": GMAgent(),
            "cgo": CGOAgent(),
            "coo": COOAgent(),
            "cro": CROAgent(),
            "cto": CTOAgent(),
        }
    return _AGENT_MAP


def get_agent_by_role(role: str) -> BaseAgent | None:
    """根据角色名获取 Agent 实例。"""
    m = _init_map()
    return m.get(role)


def get_all_chiefs() -> list[BaseAgent]:
    """获取所有 L2 首席 Agent。"""
    m = _init_map()
    return [m["cgo"], m["coo"], m["cro"], m["cto"]]

