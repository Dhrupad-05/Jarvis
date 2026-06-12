from __future__ import annotations

import re

from core.config import Settings
from computer_control.planner import ActionPlanner
from security.permissions import Capability, RiskLevel
from shared.responses import ToolResult
from tools.base_tool import BaseTool, ToolMetadata
from tools.browser.controller import BrowserController
from tools.command_parsing import quoted_or_tail


class BrowserTool(BaseTool):
    metadata = ToolMetadata(
        name="browser",
        description="Open URLs and start browser workflows",
        keywords=("open url", "go to ", "google search", "search google", "open youtube", "open github"),
        capability=Capability.BROWSER,
        risk_level=RiskLevel.LOW,
    )

    def __init__(self, settings: Settings | None = None, controller: BrowserController | None = None) -> None:
        self.controller = controller or BrowserController(settings)
        self.planner = ActionPlanner()

    def execute(self, user_text: str, *, confirmed: bool = False) -> ToolResult:
        lowered = user_text.lower()
        if "google search" in lowered or "search google" in lowered:
            parsed = self.planner.extract_search(user_text)
            query = parsed[1] if parsed else quoted_or_tail(user_text, ("google search", "search google"))
            url = self.controller.google_search(query)
            return ToolResult(True, f"Searched Google for '{query}'.", {"url": url})
        if "open youtube" in lowered:
            query = quoted_or_tail(user_text, ("open youtube",))
            url = self.controller.open_youtube(None if query.lower() == "open youtube" else query)
            return ToolResult(True, "Opened YouTube.", {"url": url})
        if "open github" in lowered:
            query = quoted_or_tail(user_text, ("open github",))
            url = self.controller.open_github(None if query.lower() == "open github" else query)
            return ToolResult(True, "Opened GitHub.", {"url": url})
        match = re.search(r"https?://\S+", user_text)
        if match:
            url = match.group(0)
        else:
            url = quoted_or_tail(user_text, ("open url", "go to"))
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
        if not self.controller.open_url(url):
            return ToolResult(False, f"Browser did not accept {url}.", {"url": url})
        return ToolResult(True, f"Opened {url}.", {"url": url})
