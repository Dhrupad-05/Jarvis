from __future__ import annotations

from core.config import Settings
from computer_control.executor import ComputerControlService
from computer_control.models import ActionType
from computer_control.planner import ActionPlanner
from security.permissions import Capability, RiskLevel
from shared.responses import ToolResult
from tools.base_tool import BaseTool, ToolMetadata


class ComputerControlTool(BaseTool):
    metadata = ToolMetadata(
        name="computer_control",
        description="Plan, resolve, execute, and verify general computer-control requests",
        keywords=("open ", "launch ", "start ", "search ", "google ", "find information", "look up "),
        capability=Capability.APPLICATIONS,
        risk_level=RiskLevel.LOW,
    )

    def __init__(
        self,
        settings: Settings,
        planner: ActionPlanner | None = None,
        service: ComputerControlService | None = None,
    ) -> None:
        self.planner = planner or ActionPlanner()
        self.service = service or ComputerControlService.from_settings(settings)

    def execute(self, user_text: str, *, confirmed: bool = False) -> ToolResult:
        plan = self.planner.plan(user_text)
        report = self.service.execute(plan)
        return ToolResult(
            success=report.success,
            message=report.message,
            data={
                "intent": report.plan.action.value,
                "target": report.plan.target_text,
                "target_type": report.target.target_type.value if report.target else None,
                "strategy": report.target.strategy.value if report.target else None,
                "duration_ms": report.duration_ms,
                "verification": report.verification,
                "error": report.error,
                "candidates": [
                    {
                        "name": candidate.name,
                        "target_type": candidate.target_type.value,
                        "strategy": candidate.strategy.value,
                        "confidence": candidate.confidence,
                    }
                    for candidate in report.candidates
                ],
            },
        )

    def risk_level(self, user_text: str) -> RiskLevel:
        action = self.planner.plan(user_text).action
        return RiskLevel.MEDIUM if action is ActionType.CLOSE else RiskLevel.LOW

    def capability(self, user_text: str) -> Capability:
        plan = self.planner.plan(user_text)
        if plan.preferred_executor == "browser" or plan.target_type.value == "website":
            return Capability.BROWSER
        if plan.action is ActionType.OPEN and " " not in plan.target_text.strip():
            return Capability.BROWSER
        if plan.target_type.value in {"file", "folder"}:
            return Capability.FILES
        return Capability.APPLICATIONS
