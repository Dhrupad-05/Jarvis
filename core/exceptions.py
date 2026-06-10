from __future__ import annotations


class AssistantError(Exception):
    """Base exception for assistant failures."""


class ConfigurationError(AssistantError):
    """Raised when configuration is invalid."""


class LLMError(AssistantError):
    """Raised when a model provider fails."""


class ToolError(AssistantError):
    """Raised when a tool cannot complete a request."""


class RoutingError(AssistantError):
    """Raised when a request cannot be routed."""


class PermissionDeniedError(AssistantError):
    """Raised when policy blocks an action."""


class VoiceError(AssistantError):
    """Raised when voice capture, transcription, or playback fails."""
