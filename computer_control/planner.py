from __future__ import annotations

import re
from dataclasses import dataclass

from computer_control.models import ActionPlan, ActionType, TargetType
from computer_control.text import clean_request


SEARCH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^find information about\s+(?P<query>.+)$", re.I),
    re.compile(r"^(?:search|look up|find)\s+(?P<engine>google|youtube|github|kaggle)?\s*(?:for|about|on)?\s*(?P<query>.+)$", re.I),
    re.compile(r"^(?P<engine>google|youtube|github|kaggle)\s+(?P<query>.+)$", re.I),
)


@dataclass(frozen=True, slots=True)
class ActionPlanner:
    """Small deterministic planner for OS-level actions.

    This keeps tool traffic out of the LLM context and gives future agentic
    planners a stable representation to reuse.
    """

    def can_plan(self, user_text: str) -> bool:
        text = clean_request(user_text).lower()
        return text.startswith(("open ", "launch ", "start ", "close ", "search ", "google ", "find ", "look up ")) or " running" in text

    def plan(self, user_text: str) -> ActionPlan:
        text = clean_request(user_text)
        lowered = text.lower()
        search = self.extract_search(text)
        if search is not None:
            engine, query = search
            return ActionPlan(
                action=ActionType.SEARCH,
                target_text=engine or "google",
                target_type=TargetType.WEBSITE,
                original_text=user_text,
                query=query,
                preferred_executor="browser",
            )
        if lowered.startswith(("close ", "quit ")):
            return ActionPlan(ActionType.CLOSE, self._strip_verb(text), TargetType.APPLICATION, user_text)
        if " running" in lowered or lowered.startswith("is "):
            return ActionPlan(ActionType.STATUS, self._strip_status(text), TargetType.APPLICATION, user_text)
        if lowered.startswith(("open ", "launch ", "start ")):
            target = self._strip_verb(text)
            target_type = self._infer_open_target(target)
            return ActionPlan(ActionType.OPEN, target, target_type, user_text)
        return ActionPlan(ActionType.FIND, text, TargetType.UNKNOWN, user_text)

    def extract_search(self, text: str) -> tuple[str | None, str] | None:
        cleaned = clean_request(text)
        for pattern in SEARCH_PATTERNS:
            match = pattern.match(cleaned)
            if not match:
                continue
            groups = match.groupdict()
            query = (groups.get("query") or "").strip()
            engine = groups.get("engine")
            if query:
                return (engine.lower() if engine else None, self._clean_query(query))
        return None

    def _strip_verb(self, text: str) -> str:
        return re.sub(r"^(open|launch|start|close|quit)\s+", "", text, flags=re.I).strip()

    def _strip_status(self, text: str) -> str:
        text = re.sub(r"^is\s+", "", text, flags=re.I)
        text = re.sub(r"\s+running\??$", "", text, flags=re.I)
        return text.strip()

    def _infer_open_target(self, target: str) -> TargetType:
        lowered = target.lower()
        if lowered.startswith(("http://", "https://", "www.")) or "." in lowered and " " not in lowered:
            return TargetType.WEBSITE
        if any(word in lowered for word in ("folder", "downloads", "desktop", "documents", "project")):
            return TargetType.FOLDER
        return TargetType.UNKNOWN

    def _clean_query(self, query: str) -> str:
        query = re.sub(r"^(for|about|on)\s+", "", query.strip(), flags=re.I)
        return query.strip(" ?.")
