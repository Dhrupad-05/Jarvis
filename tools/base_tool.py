from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from shared.responses import ToolResult
from security.permissions import Capability, RiskLevel


@dataclass(frozen=True, slots=True)
class ToolMetadata:
    name: str
    description: str
    keywords: tuple[str, ...]
    capability: Capability
    risk_level: RiskLevel
    enabled: bool = True


class BaseTool(ABC):
    metadata: ToolMetadata

    def risk_level(self, user_text: str) -> RiskLevel:
        return self.metadata.risk_level

    @abstractmethod
    def execute(self, user_text: str, *, confirmed: bool = False) -> ToolResult:
        """Run the tool and return a structured result."""
