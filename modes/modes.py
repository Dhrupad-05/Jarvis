from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AssistantMode:
    name: str
    description: str
    behavior_rules: tuple[str, ...]
    proactive_enabled: bool
    automation_enabled: bool
    voice_listening_enabled: bool = True
    browser_control_enabled: bool = True
    system_control_enabled: bool = True

    def build_system_prompt(self, assistant_name: str) -> str:
        rules = "\n".join(f"- {rule}" for rule in self.behavior_rules)
        safety = (
            "Automation is disabled unless a future tool explicitly allows it."
            if not self.automation_enabled
            else "Automation may be suggested, but execute only through approved tools."
        )
        return (
            f"You are {assistant_name}, a local-first personal AI assistant.\n"
            f"Active mode: {self.name}.\n"
            f"Mode description: {self.description}\n"
            f"Behavior rules:\n{rules}\n"
            f"{safety}\n"
            "Be concise, practical, and preserve user privacy. "
            "Do not claim access to capabilities that are not implemented."
        )

    def allows_capability(self, capability: str) -> bool:
        if capability == "voice":
            return self.voice_listening_enabled
        if capability == "browser":
            return self.browser_control_enabled and self.automation_enabled
        if capability == "system":
            return self.system_control_enabled and self.automation_enabled
        if capability in {"applications", "files"}:
            return self.automation_enabled
        return True


def default_modes() -> dict[str, AssistantMode]:
    return {
        "study": AssistantMode(
            name="Study",
            description="Tutor-like help for learning, explanations, summaries, and recall.",
            behavior_rules=(
                "Teach step by step.",
                "Prefer examples, checks for understanding, and concise summaries.",
                "Adapt explanations to the user's current level.",
            ),
            proactive_enabled=True,
            automation_enabled=False,
            browser_control_enabled=False,
            system_control_enabled=False,
        ),
        "productivity": AssistantMode(
            name="Productivity",
            description="Task-oriented assistant for planning, prioritization, and execution support.",
            behavior_rules=(
                "Focus on next actions and clear decisions.",
                "Keep responses short unless the task requires depth.",
                "Separate planning from execution when tools are involved.",
            ),
            proactive_enabled=True,
            automation_enabled=True,
        ),
        "research": AssistantMode(
            name="Research",
            description="Careful analysis mode for exploration, comparison, and synthesis.",
            behavior_rules=(
                "State assumptions and uncertainty.",
                "Structure findings clearly.",
                "Prefer source-aware reasoning when sources are available.",
            ),
            proactive_enabled=True,
            automation_enabled=True,
            system_control_enabled=False,
        ),
        "interview": AssistantMode(
            name="Interview",
            description="Silent-safe mode for interviews and high-stakes contexts.",
            behavior_rules=(
                "Do not be proactive.",
                "Do not suggest monitoring, screen reading, or automation.",
                "Answer only what is asked, briefly and directly.",
            ),
            proactive_enabled=False,
            automation_enabled=False,
            voice_listening_enabled=False,
            browser_control_enabled=False,
            system_control_enabled=False,
        ),
    }
