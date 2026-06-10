from __future__ import annotations

import shlex
from pathlib import Path

from core.config import Settings
from core.exceptions import ToolError
from security.permissions import Capability, RiskLevel
from shared.responses import ToolResult
from tools.base_tool import BaseTool, ToolMetadata
from tools.command_parsing import quoted_or_tail, safe_path
from tools.files.manager import FileManager


class FileTool(BaseTool):
    metadata = ToolMetadata(
        name="files",
        description="Create, rename, move, copy, delete, and search files",
        keywords=("create file", "create folder", "make folder", "rename ", "move ", "copy ", "delete ", "search files", "find file"),
        capability=Capability.FILES,
        risk_level=RiskLevel.MEDIUM,
    )

    def __init__(self, settings: Settings | None = None, manager: FileManager | None = None) -> None:
        root = settings.project_root if settings else Path.cwd()
        self.root = root
        self.manager = manager or FileManager(root)

    def execute(self, user_text: str, *, confirmed: bool = False) -> ToolResult:
        lowered = user_text.lower()
        if lowered.startswith(("create folder", "make folder")):
            path = safe_path(self.root, quoted_or_tail(user_text, ("create folder", "make folder")))
            self.manager.create_folder(path)
            return ToolResult(True, f"Created folder {path}.", {"path": str(path)})
        if lowered.startswith("create file"):
            path = safe_path(self.root, quoted_or_tail(user_text, ("create file",)))
            self.manager.create_file(path)
            return ToolResult(True, f"Created file {path}.", {"path": str(path)})
        if lowered.startswith(("search files", "find file")):
            query = quoted_or_tail(user_text, ("search files", "find file"))
            matches = self.manager.search(query)
            return ToolResult(True, "\n".join(str(p) for p in matches) or "No matches found.", {"matches": [str(p) for p in matches]})
        if lowered.startswith(("rename ", "move ", "copy ", "delete ")):
            return self._two_path_operation(user_text)
        raise ToolError("Unsupported file command.")

    def _two_path_operation(self, user_text: str) -> ToolResult:
        tokens = shlex.split(user_text.replace("--confirm", ""))
        op = tokens[0].lower()
        if op == "delete":
            if len(tokens) < 2:
                raise ToolError("Delete requires a path.")
            path = safe_path(self.root, tokens[1])
            self.manager.delete(path)
            return ToolResult(True, f"Deleted {path}.", {"path": str(path)})
        if len(tokens) < 3:
            raise ToolError(f"{op.title()} requires source and destination paths.")
        source = safe_path(self.root, tokens[1])
        target = safe_path(self.root, tokens[2])
        if op == "rename":
            self.manager.rename(source, target)
        elif op == "move":
            self.manager.move(source, target)
        elif op == "copy":
            self.manager.copy(source, target)
        else:
            raise ToolError("Unsupported file operation.")
        return ToolResult(True, f"{op.title()}d {source} to {target}.", {"source": str(source), "target": str(target)})

    def risk_level(self, user_text: str) -> RiskLevel:
        lowered = user_text.lower()
        if lowered.startswith(("create folder", "make folder", "create file", "search files", "find file")):
            return RiskLevel.LOW
        if "delete" in lowered:
            return RiskLevel.HIGH if "*" in lowered else RiskLevel.MEDIUM
        return RiskLevel.MEDIUM
