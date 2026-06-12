from __future__ import annotations

import re

from memory.memory_intents import MemoryIntentClassifier, MemoryIntentType
from memory.memory_manager import MemoryManager
from memory.memory_types import MemoryType
from modes.mode_manager import ModeManager
from security.permissions import Capability, RiskLevel
from shared.responses import ToolResult
from tools.base_tool import BaseTool, ToolMetadata


class MemoryTool(BaseTool):
    metadata = ToolMetadata(
        name="memory",
        description="Store and retrieve assistant memory",
        keywords=(
            "remember ",
            "recall ",
            "search memory",
            "what do you remember",
            "forget memory",
            "summarize memory",
            "what is my ",
            "what's my ",
            "which project",
            "what project",
            "who uses ",
        ),
        capability=Capability.MEMORY,
        risk_level=RiskLevel.LOW,
    )

    def __init__(self, memory_manager: MemoryManager, mode_manager: ModeManager) -> None:
        self.memory_manager = memory_manager
        self.mode_manager = mode_manager
        self.classifier = MemoryIntentClassifier()

    def matches(self, normalized_text: str) -> bool:
        if super().matches(normalized_text):
            return True
        intent = self.classifier.classify(normalized_text)
        return intent.intent_type is not MemoryIntentType.NONE and intent.confidence >= 0.7

    def execute(self, user_text: str, *, confirmed: bool = False) -> ToolResult:
        lowered = user_text.lower().strip()
        intent = self.classifier.classify(user_text)
        if intent.intent_type is MemoryIntentType.STORE:
            record = self.memory_manager.remember(
                intent.content,
                memory_type=intent.memory_type,
                source="explicit_user_memory",
                mode=self.mode_manager.active_mode,
            )
            if record is None:
                return ToolResult(False, "Memory storage failed validation or is disabled in this mode.")
            return ToolResult(True, f"Remembered memory #{record.id}.", {"id": record.id, "type": record.memory_type.value})
        if lowered.startswith(("recall ", "search memory")):
            query = re.sub(r"^(recall|search memory)\s+", "", user_text, flags=re.I).strip()
            return self._search_response(query, limit=5)
        if intent.intent_type is MemoryIntentType.QUERY or self._looks_like_memory_question(lowered):
            return self._search_response(user_text, limit=1)
        if intent.intent_type is MemoryIntentType.DELETE:
            return self._delete_from_text(user_text)
        if intent.intent_type is MemoryIntentType.SUMMARY:
            return ToolResult(True, self.memory_manager.summarize())
        if lowered.startswith("forget memory"):
            return self._delete_from_text(user_text)
        if lowered.startswith(("summarize memory", "what do you remember")):
            return ToolResult(True, self.memory_manager.summarize())
        return ToolResult(False, "Unsupported memory command.")

    def developer_command(self, command: str) -> ToolResult:
        lowered = command.lower().strip()
        if lowered == "stats":
            stats = self.memory_manager.stats()
            details = ", ".join(f"{key}: {value}" for key, value in sorted(stats.items()))
            return ToolResult(True, details, stats)
        if lowered == "list":
            return ToolResult(True, self.memory_manager.export_text())
        if lowered.startswith("show "):
            match = re.search(r"(\d+)", lowered)
            if not match:
                return ToolResult(False, "Please provide a memory id.")
            record = self.memory_manager.store.get(int(match.group(1)))
            if record is None:
                return ToolResult(False, "Memory not found.")
            return ToolResult(True, f"#{record.id} [{record.memory_type.value}] {record.content}")
        if lowered.startswith("search "):
            return self._search_response(command.split(" ", 1)[1].strip(), limit=10)
        if lowered.startswith("delete "):
            match = re.search(r"(\d+)", lowered)
            if not match:
                return ToolResult(False, "Please provide a memory id.")
            deleted = self.memory_manager.delete(int(match.group(1)))
            return ToolResult(deleted, "Deleted memory." if deleted else "Memory not found.")
        if lowered == "export":
            return ToolResult(True, self.memory_manager.export_text())
        return ToolResult(False, "Usage: /memory stats|list|search <query>|delete <id>|export")

    def _infer_type(self, content: str) -> MemoryType:
        return self.classifier.infer_type(content)

    def _search_response(self, query: str, *, limit: int) -> ToolResult:
        records = self.memory_manager.search(query, limit=limit)
        if not records:
            return ToolResult(True, "Memory not found.", {"matches": []})
        message = "\n".join(f"#{record.id} [{record.memory_type.value}] {record.content}" for record in records)
        return ToolResult(True, message, {"matches": [record.id for record in records]})

    def _looks_like_memory_question(self, lowered: str) -> bool:
        return lowered.startswith(("what is my ", "what's my ", "which project", "what project", "who uses "))

    def _delete_from_text(self, user_text: str) -> ToolResult:
        match = re.search(r"(\d+)", user_text)
        if not match:
            return ToolResult(False, "Please provide a memory id to forget.")
        deleted = self.memory_manager.delete(int(match.group(1)))
        return ToolResult(deleted, "Forgot memory." if deleted else "Memory not found.")
