from __future__ import annotations

import argparse

from brain.llm import OllamaClient
from brain.session import ChatSession
from core.config import Settings
from core.logger import configure_logging, get_logger
from modes.mode_manager import ModeManager
from router.router import RequestRouter
from security.permissions import PermissionPolicy
from tools.registry import ToolRegistry, build_default_registry
from voice.voice_manager import VoiceManager


def build_session(settings: Settings) -> ChatSession:
    modes = ModeManager.from_settings(settings)
    policy = PermissionPolicy(
        require_confirmation_for_medium=settings.require_confirmation_for_medium,
        require_confirmation_for_high=settings.require_confirmation_for_high,
    )
    registry: ToolRegistry = build_default_registry(settings=settings, mode_manager=modes, permission_policy=policy)
    llm = OllamaClient(settings=settings)
    router = RequestRouter(tool_registry=registry, mode_manager=modes)
    return ChatSession(settings=settings, llm=llm, router=router, mode_manager=modes)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local-first AI assistant")
    parser.add_argument("--voice", action="store_true", help="Start push-to-talk voice mode")
    parser.add_argument("--once", help="Handle one text request and exit")
    args = parser.parse_args()

    settings = Settings.load()
    configure_logging(settings)
    log = get_logger(__name__)
    session = build_session(settings)

    if args.once:
        try:
            print("".join(session.handle_stream(args.once)))
        except Exception as exc:
            log.exception("One-shot request failed")
            print(f"Error: {exc}")
            return 1
        return 0

    if args.voice:
        voice = VoiceManager.from_settings(settings=settings, session=session)
        return voice.conversation_loop()

    print(f"{settings.assistant_name} local assistant")
    print("Type /mode <study|productivity|research|interview>, /modes, /reset, or /exit.")
    print(f"Active mode: {session.mode_manager.active_mode.name}")

    while True:
        try:
            user_text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return 0

        if not user_text:
            continue
        if user_text.lower() in {"/exit", "exit", "quit", "/quit"}:
            print("Goodbye.")
            return 0
        if user_text.lower() == "/reset":
            session.reset()
            print("Session reset.")
            continue
        if user_text.lower() == "/modes":
            print("Modes: " + ", ".join(session.mode_manager.available_mode_names()))
            continue
        if user_text.lower().startswith("/memory"):
            command = user_text[len("/memory") :].strip() or "stats"
            try:
                result = session.router.tool_registry.get("memory").developer_command(command)  # type: ignore[attr-defined]
                print(result.message)
            except Exception as exc:
                log.exception("Memory command failed")
                print(f"Memory command failed: {exc}")
            continue
        if user_text.lower().startswith("/mode "):
            mode_name = user_text.split(maxsplit=1)[1]
            try:
                mode = session.mode_manager.set_mode(mode_name)
                print(f"Active mode: {mode.name}")
            except ValueError as exc:
                print(str(exc))
            continue

        try:
            print(f"{settings.assistant_name}: ", end="", flush=True)
            for chunk in session.handle_stream(user_text):
                print(chunk, end="", flush=True)
            print()
        except Exception as exc:  # CLI boundary: keep process alive.
            log.exception("Request failed")
            print(f"\nError: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
