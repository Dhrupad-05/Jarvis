from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IntentType(str, Enum):
    CHAT = "chat"
    TOOL = "tool"
    MODE_SWITCH = "mode_switch"
    FUTURE_CAPABILITY = "future_capability"


@dataclass(frozen=True, slots=True)
class Intent:
    intent_type: IntentType
    confidence: float
    reason: str


@dataclass(frozen=True, slots=True)
class RouteDecision:
    intent: Intent
    tool_name: str | None = None
    target_mode: str | None = None

