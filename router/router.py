from __future__ import annotations

from dataclasses import dataclass

from modes.mode_manager import ModeManager
from router.intents import Intent, IntentType, RouteDecision
from shared.responses import ToolResult
from shared.utils import normalize_text
from tools.command_parsing import has_confirmation, strip_confirmation
from tools.registry import ToolRegistry


@dataclass(slots=True)
class RequestRouter:
    """Routes requests to tools, future modules, mode changes, or the LLM."""

    tool_registry: ToolRegistry
    mode_manager: ModeManager

    def route(self, user_text: str) -> RouteDecision:
        text = normalize_text(user_text).lower()

        mode = self._extract_mode(text)
        if mode:
            return RouteDecision(
                intent=Intent(IntentType.MODE_SWITCH, 0.98, "User requested mode switch."),
                target_mode=mode,
            )

        tool_name = self.tool_registry.match(text)
        if tool_name:
            return RouteDecision(
                intent=Intent(IntentType.TOOL, 0.75, "Matched registered tool capability."),
                tool_name=tool_name,
            )

        if any(term in text for term in ("screenshot", "ocr", "screen", "summarize pdf", "youtube")):
            return RouteDecision(
                intent=Intent(IntentType.FUTURE_CAPABILITY, 0.6, "Recognized future capability; use LLM for now.")
            )

        return RouteDecision(intent=Intent(IntentType.CHAT, 0.7, "Default conversational route."))

    def execute_tool(self, tool_name: str, user_text: str) -> ToolResult:
        confirmed = has_confirmation(user_text)
        return self.tool_registry.execute(tool_name, strip_confirmation(user_text), confirmed=confirmed)

    def _extract_mode(self, text: str) -> str | None:
        prefixes = ("switch to ", "change to ", "enter ")
        for prefix in prefixes:
            if text.startswith(prefix) and text.endswith(" mode"):
                return text.removeprefix(prefix).removesuffix(" mode").strip()
        if text.startswith("/mode "):
            return text.split(maxsplit=1)[1].strip()
        return None
