from __future__ import annotations

from core.exceptions import ToolError
from security.permissions import Capability, RiskLevel
from shared.responses import ToolResult
from tools.applications.manager import ApplicationManager
from tools.base_tool import BaseTool, ToolMetadata


class ApplicationTool(BaseTool):
    metadata = ToolMetadata(
        name="applications",
        description="Open, close, or inspect local applications",
        keywords=("open chrome", "open notepad", "open calculator", "open vscode", "open vs code", "open spotify", "close ", "is chrome running", "is notepad running"),
        capability=Capability.APPLICATIONS,
        risk_level=RiskLevel.LOW,
    )

    def __init__(self, manager: ApplicationManager | None = None) -> None:
        self.manager = manager or ApplicationManager.windows_defaults()

    def execute(self, user_text: str, *, confirmed: bool = False) -> ToolResult:
        spec = self.manager.resolve(user_text)
        if spec is None:
            raise ToolError("I do not know which supported application you mean.")
        lowered = user_text.lower()
        if "close" in lowered:
            closed = self.manager.close(spec)
            return ToolResult(closed, f"{'Closed' if closed else 'Could not find running'} {spec.name}.")
        if "running" in lowered or "status" in lowered:
            running = self.manager.is_running(spec)
            return ToolResult(True, f"{spec.name} is {'running' if running else 'not running'}.", {"running": running})
        self.manager.open(spec)
        return ToolResult(True, f"Opened {spec.name}.", {"application": spec.name})

    def risk_level(self, user_text: str) -> RiskLevel:
        return RiskLevel.MEDIUM if "close" in user_text.lower() else RiskLevel.LOW
