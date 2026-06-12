from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

from brain.llm import LLMClient
from core.audit import log_action
from core.config import Settings
from core.logger import get_logger
from modes.mode_manager import ModeManager
from router.intents import IntentType
from router.router import RequestRouter
from shared.models import Message, Role, SessionState

log = get_logger(__name__)


@dataclass(slots=True)
class ChatSession:
    """Coordinates mode context, routing, tools, model calls, and history."""

    settings: Settings
    llm: LLMClient
    router: RequestRouter
    mode_manager: ModeManager
    state: SessionState = field(default_factory=SessionState)

    def handle_stream(self, user_text: str) -> Iterator[str]:
        user_message = Message(role=Role.USER, content=user_text)
        log_action("user_input", "received", chars=len(user_text))
        try:
            route = self.router.route(user_text)
        except Exception as exc:
            log.exception("Routing failed")
            text = f"I could not route that request safely: {exc}"
            self._append_turn(user_message, text)
            yield text
            return

        if route.intent.intent_type is IntentType.MODE_SWITCH and route.target_mode:
            mode = self.mode_manager.set_mode(route.target_mode)
            text = f"Switched to {mode.name} mode."
            self._append_turn(user_message, text)
            yield text
            return

        if route.tool_name:
            try:
                result = self.router.execute_tool(route.tool_name, user_text)
            except Exception as exc:
                log.exception("Tool execution escaped safety boundary")
                result_text = f"The tool failed safely: {exc}"
                self._append_turn(user_message, result_text)
                yield result_text
                return
            text = result.message
            self._append_turn(user_message, text)
            yield text
            return

        self.state.messages.append(user_message)
        self._trim_history()
        chunks: list[str] = []
        system_prompt = self.mode_manager.active_mode.build_system_prompt(self.settings.assistant_name)
        for chunk in self.llm.stream_chat(self.state.messages, system_prompt):
            chunks.append(chunk)
            yield chunk
        self.state.messages.append(Message(role=Role.ASSISTANT, content="".join(chunks)))
        self._trim_history()

    def reset(self) -> None:
        self.state = SessionState()

    def _append_turn(self, user_message: Message, assistant_text: str) -> None:
        self.state.messages.extend(
            [user_message, Message(role=Role.ASSISTANT, content=assistant_text)]
        )
        self._trim_history()

    def _trim_history(self) -> None:
        max_messages = self.settings.max_history_messages
        if len(self.state.messages) > max_messages:
            self.state.messages = self.state.messages[-max_messages:]
