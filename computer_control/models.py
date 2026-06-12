from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class ActionType(str, Enum):
    OPEN = "open"
    CLOSE = "close"
    SEARCH = "search"
    STATUS = "status"
    FIND = "find"


class TargetType(str, Enum):
    APPLICATION = "application"
    WEBSITE = "website"
    FILE = "file"
    FOLDER = "folder"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ResolutionStrategy(str, Enum):
    KNOWN_REGISTRY = "known_registry"
    START_MENU = "start_menu"
    INSTALLED_APPLICATION = "installed_application"
    PATH_EXECUTABLE = "path_executable"
    SHELL_EXECUTION = "shell_execution"
    WINDOWS_SEARCH = "windows_search"
    DOMAIN_HEURISTIC = "domain_heuristic"
    URL_LITERAL = "url_literal"
    SPECIAL_FOLDER = "special_folder"
    FILESYSTEM_SEARCH = "filesystem_search"
    SEARCH_ENGINE = "search_engine"
    CLARIFICATION = "clarification"


@dataclass(frozen=True, slots=True)
class ActionPlan:
    action: ActionType
    target_text: str
    target_type: TargetType
    original_text: str
    query: str | None = None
    preferred_executor: str | None = None


@dataclass(frozen=True, slots=True)
class ResolvedTarget:
    name: str
    target_type: TargetType
    value: str | Path
    strategy: ResolutionStrategy
    confidence: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ExecutionReport:
    success: bool
    message: str
    plan: ActionPlan
    target: ResolvedTarget | None = None
    duration_ms: float = 0.0
    verification: str | None = None
    error: str | None = None
    candidates: list[ResolvedTarget] = field(default_factory=list)
