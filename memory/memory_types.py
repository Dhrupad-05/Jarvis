from __future__ import annotations

from enum import Enum


class MemoryType(str, Enum):
    PREFERENCE = "preference"
    PROJECT = "project"
    GOAL = "goal"
    TASK = "task"
    LEARNING_NOTE = "learning_note"
    CODING_CONTEXT = "coding_context"
    GENERAL_NOTE = "general_note"
    CONVERSATION_SUMMARY = "conversation_summary"
    ASSISTANT_OBSERVATION = "assistant_observation"

