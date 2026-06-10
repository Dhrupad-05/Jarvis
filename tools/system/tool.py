from __future__ import annotations

import re

from security.permissions import Capability, RiskLevel
from shared.responses import ToolResult
from tools.base_tool import BaseTool, ToolMetadata
from tools.system.manager import SystemManager


class SystemTool(BaseTool):
    metadata = ToolMetadata(
        name="system",
        description="Control local system settings",
        keywords=("mute", "volume up", "volume down", "brightness", "lock workstation", "sleep", "shutdown", "restart"),
        capability=Capability.SYSTEM,
        risk_level=RiskLevel.HIGH,
    )

    def __init__(self, manager: SystemManager | None = None) -> None:
        self.manager = manager or SystemManager()

    def execute(self, user_text: str, *, confirmed: bool = False) -> ToolResult:
        lowered = user_text.lower()
        if "mute" in lowered:
            self.manager.mute()
            return ToolResult(True, "Toggled mute.")
        if "volume up" in lowered:
            self.manager.volume_key("up")
            return ToolResult(True, "Raised volume.")
        if "volume down" in lowered:
            self.manager.volume_key("down")
            return ToolResult(True, "Lowered volume.")
        if "brightness" in lowered:
            match = re.search(r"(\d{1,3})", lowered)
            value = int(match.group(1)) if match else 50
            self.manager.set_brightness(value)
            return ToolResult(True, f"Set brightness to {max(0, min(100, value))}%.")
        if "lock" in lowered:
            self.manager.lock()
            return ToolResult(True, "Locked workstation.")
        if "sleep" in lowered:
            self.manager.sleep()
            return ToolResult(True, "Sleep command issued.")
        if "shutdown" in lowered:
            self.manager.shutdown()
            return ToolResult(True, "Shutdown scheduled in 60 seconds.")
        if "restart" in lowered:
            self.manager.restart()
            return ToolResult(True, "Restart scheduled in 60 seconds.")
        return ToolResult(False, "Unsupported system command.")

    def risk_level(self, user_text: str) -> RiskLevel:
        lowered = user_text.lower()
        if any(term in lowered for term in ("shutdown", "restart", "sleep", "lock")):
            return RiskLevel.HIGH
        return RiskLevel.LOW
