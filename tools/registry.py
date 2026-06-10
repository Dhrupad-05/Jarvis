from __future__ import annotations

from dataclasses import dataclass, field

from core.audit import log_action
from core.config import Settings
from modes.mode_manager import ModeManager
from security.permissions import Capability, PermissionPolicy, RiskLevel
from core.exceptions import ToolError
from shared.responses import ToolResult
from tools.base_tool import BaseTool, ToolMetadata


class PlaceholderTool(BaseTool):
    def __init__(self, metadata: ToolMetadata) -> None:
        self.metadata = metadata

    def execute(self, user_text: str, *, confirmed: bool = False) -> ToolResult:
        return ToolResult(
            success=True,
            message=(
                f"{self.metadata.description} is registered but not active in this phase. "
                "This request was safely recognized for a future capability."
            ),
            data={"tool": self.metadata.name, "input": user_text},
        )


@dataclass(slots=True)
class ToolRegistry:
    tools: dict[str, BaseTool] = field(default_factory=dict)
    mode_manager: ModeManager | None = None
    permission_policy: PermissionPolicy = field(default_factory=PermissionPolicy)

    def register(self, tool: BaseTool) -> None:
        self.tools[tool.metadata.name] = tool

    def get(self, name: str) -> BaseTool:
        try:
            return self.tools[name]
        except KeyError as exc:
            raise ToolError(f"Tool not registered: {name}") from exc

    def match(self, normalized_text: str) -> str | None:
        for name, tool in self.tools.items():
            if not tool.metadata.enabled:
                continue
            if any(keyword in normalized_text for keyword in tool.metadata.keywords):
                return name
        return None

    def execute(self, name: str, user_text: str, *, confirmed: bool = False) -> ToolResult:
        tool = self.get(name)
        if self.mode_manager is not None:
            risk = tool.risk_level(user_text)
            decision = self.permission_policy.evaluate(
                mode=self.mode_manager.active_mode,
                capability=tool.metadata.capability,
                risk=risk,
                confirmed=confirmed,
            )
            if decision.requires_confirmation:
                log_action(
                    "tool_confirmation_required",
                    "blocked",
                    tool=name,
                    risk=risk.value,
                    mode=self.mode_manager.active_mode.name,
                )
                return ToolResult(
                    success=False,
                    message=f"{decision.reason} Re-run with '--confirm' if you intend this action.",
                    data={"tool": name, "risk": risk.value},
                    requires_confirmation=True,
                )
            if not decision.allowed:
                log_action("tool_blocked", "blocked", tool=name, reason=decision.reason)
                return ToolResult(success=False, message=decision.reason, data={"tool": name})
        result = tool.execute(user_text, confirmed=confirmed)
        log_action("tool_execute", "success" if result.success else "failed", tool=name, message=result.message)
        return result


def build_default_registry(
    settings: Settings | None = None,
    mode_manager: ModeManager | None = None,
    permission_policy: PermissionPolicy | None = None,
) -> ToolRegistry:
    from tools.applications.tool import ApplicationTool
    from tools.browser.tool import BrowserTool
    from tools.files.tool import FileTool
    from tools.system.tool import SystemTool

    registry = ToolRegistry(
        mode_manager=mode_manager,
        permission_policy=permission_policy or PermissionPolicy(),
    )
    registry.register(ApplicationTool())
    registry.register(BrowserTool(settings=settings))
    registry.register(FileTool(settings=settings))
    registry.register(SystemTool())
    registry.register(
        PlaceholderTool(
            ToolMetadata(
                name="vision",
                description="Vision and screen analysis",
                keywords=("analyze screenshot", "read screen", "ocr"),
                capability=Capability.BROWSER,
                risk_level=RiskLevel.LOW,
            )
        )
    )
    registry.register(
        PlaceholderTool(
            ToolMetadata(
                name="study",
                description="Study document processing",
                keywords=("summarize pdf", "make flashcards", "create mcq"),
                capability=Capability.FILES,
                risk_level=RiskLevel.LOW,
            )
        )
    )
    return registry
