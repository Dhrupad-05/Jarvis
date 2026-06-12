from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from modes.modes import AssistantMode


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Capability(str, Enum):
    APPLICATIONS = "applications"
    BROWSER = "browser"
    FILES = "files"
    SYSTEM = "system"
    VOICE = "voice"
    MEMORY = "memory"


@dataclass(frozen=True, slots=True)
class PermissionDecision:
    allowed: bool
    requires_confirmation: bool
    reason: str


@dataclass(frozen=True, slots=True)
class PermissionPolicy:
    require_confirmation_for_medium: bool = True
    require_confirmation_for_high: bool = True

    def evaluate(
        self,
        *,
        mode: AssistantMode,
        capability: Capability,
        risk: RiskLevel,
        confirmed: bool = False,
    ) -> PermissionDecision:
        if not mode.allows_capability(capability.value):
            return PermissionDecision(False, False, f"{mode.name} mode disables {capability.value}.")
        if risk is RiskLevel.HIGH and self.require_confirmation_for_high and not confirmed:
            return PermissionDecision(False, True, "High-risk action requires confirmation.")
        if risk is RiskLevel.MEDIUM and self.require_confirmation_for_medium and not confirmed:
            return PermissionDecision(False, True, "Medium-risk action requires confirmation.")
        return PermissionDecision(True, False, "Allowed.")
