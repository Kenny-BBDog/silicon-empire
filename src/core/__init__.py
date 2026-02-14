"""Silicon-Empire core package."""

from src.core.state import SiliconState, CritiqueEntry, DecisionMatrix
from src.core.envelope import Envelope, EnvelopeHeader, create_envelope
from src.core.memory import MemoryManager, get_memory
from src.core.bus import MessageBus, get_bus
from src.core.cost_tracker import CostTracker
from src.core.guards import requires_approval, auto_judge, check_mcp_permission
from src.core.personal_memory import PersonalMemory, MemoryEntry

__all__ = [
    "SiliconState",
    "CritiqueEntry",
    "DecisionMatrix",
    "Envelope",
    "EnvelopeHeader",
    "create_envelope",
    "MemoryManager",
    "get_memory",
    "MessageBus",
    "get_bus",
    "CostTracker",
    "requires_approval",
    "auto_judge",
    "check_mcp_permission",
    "PersonalMemory",
    "MemoryEntry",
]
