from __future__ import annotations

import re
from pathlib import Path

from coding.coding_manager import CodingManager
from core.config import Settings
from memory.memory_manager import MemoryManager
from security.permissions import Capability, RiskLevel
from shared.responses import ToolResult
from tools.base_tool import BaseTool, ToolMetadata


class CodingTool(BaseTool):
    metadata = ToolMetadata(
        name="coding",
        description="Repository indexing, error analysis, and coding context assistance",
        keywords=("analyze repo", "index repo", "explain error", "analyze error", "explain code", "coding task"),
        capability=Capability.MEMORY,
        risk_level=RiskLevel.LOW,
    )

    def __init__(self, settings: Settings, memory_manager: MemoryManager) -> None:
        self.settings = settings
        self.manager = CodingManager(memory_manager)

    def execute(self, user_text: str, *, confirmed: bool = False) -> ToolResult:
        lowered = user_text.lower()
        if lowered.startswith(("analyze repo", "index repo")):
            root = self._path_arg(user_text) or self.settings.project_root
            summary = self.manager.index_repository(root)
            return ToolResult(True, summary.compact(), {"root": str(summary.root), "files": len(summary.files)})
        if lowered.startswith(("explain error", "analyze error")):
            text = re.sub(r"^(explain error|analyze error)\s*", "", user_text, flags=re.I).strip()
            analysis = self.manager.analyze_error(text)
            return ToolResult(True, analysis.format())
        if lowered.startswith("explain code"):
            code = user_text.split(" ", 2)[2] if len(user_text.split(" ", 2)) == 3 else ""
            return ToolResult(True, self.manager.explain_code(code))
        if lowered.startswith("coding task"):
            task = user_text.split(" ", 2)[2] if len(user_text.split(" ", 2)) == 3 else ""
            self.manager.track_task(task)
            return ToolResult(True, "Tracked coding task.")
        return ToolResult(False, "Unsupported coding command.")

    def _path_arg(self, text: str) -> Path | None:
        match = re.search(r'"([^"]+)"', text)
        if not match:
            return None
        path = Path(match.group(1)).expanduser()
        return path if path.is_absolute() else (self.settings.project_root / path)
