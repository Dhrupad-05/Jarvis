from __future__ import annotations

from dataclasses import dataclass

from brain.session import ChatSession
from core.audit import log_action
from core.config import Settings
from core.exceptions import VoiceError
from security.permissions import Capability, PermissionPolicy, RiskLevel
from voice.microphone import MicrophoneRecorder
from voice.stt import WhisperTranscriber
from voice.tts import PiperSpeaker
from voice.diagnostics import VoiceDiagnostics, run_voice_diagnostics


@dataclass(slots=True)
class VoiceManager:
    settings: Settings
    session: ChatSession
    recorder: MicrophoneRecorder
    transcriber: WhisperTranscriber
    speaker: PiperSpeaker
    permission_policy: PermissionPolicy

    @classmethod
    def from_settings(cls, settings: Settings, session: ChatSession) -> "VoiceManager":
        return cls(
            settings=settings,
            session=session,
            recorder=MicrophoneRecorder(),
            transcriber=WhisperTranscriber(settings),
            speaker=PiperSpeaker(settings),
            permission_policy=PermissionPolicy(
                require_confirmation_for_medium=settings.require_confirmation_for_medium,
                require_confirmation_for_high=settings.require_confirmation_for_high,
            ),
        )

    def listen(self, seconds: float = 5.0) -> str:
        decision = self.permission_policy.evaluate(
            mode=self.session.mode_manager.active_mode,
            capability=Capability.VOICE,
            risk=RiskLevel.LOW,
        )
        if not decision.allowed:
            raise VoiceError(decision.reason)
        audio_path = None
        try:
            audio_path = self.recorder.record_push_to_talk(seconds=seconds)
            text = self.transcriber.transcribe(audio_path)
            log_action("voice_listen", "success", chars=len(text))
            return text
        except VoiceError:
            raise
        except Exception as exc:
            raise VoiceError(f"Voice listening failed: {exc}") from exc
        finally:
            if audio_path is not None:
                try:
                    audio_path.unlink(missing_ok=True)
                    log_action("voice_temp_cleanup", "success", file=str(audio_path))
                except Exception as exc:
                    log_action("voice_temp_cleanup", "failed", file=str(audio_path), error=str(exc))

    def speak(self, text: str) -> None:
        try:
            self.speaker.speak(text)
        except VoiceError:
            raise
        except Exception as exc:
            raise VoiceError(f"Voice playback failed: {exc}") from exc

    def validate_startup(self) -> VoiceDiagnostics:
        diagnostics = run_voice_diagnostics(self.settings)
        log_action(
            "voice_startup_validation",
            "success" if diagnostics.usable_for_listening and diagnostics.usable_for_speaking else "failed",
            messages=diagnostics.messages(),
        )
        return diagnostics

    def conversation_loop(self) -> int:
        diagnostics = self.validate_startup()
        if not diagnostics.usable_for_listening or not diagnostics.usable_for_speaking:
            print("Voice mode is not ready:")
            for message in diagnostics.messages():
                print(f"- {message}")
            return 1
        if not self.session.mode_manager.active_mode.voice_listening_enabled:
            print("Voice listening is disabled in the active mode.")
            return 1
        print("Voice mode: press Enter to record, type /exit to quit.")
        while True:
            command = input("\nPush-to-talk ready: ").strip().lower()
            if command in {"/exit", "exit", "quit"}:
                return 0
            try:
                user_text = self.listen()
                if not user_text:
                    print("No speech detected.")
                    continue
                print(f"You: {user_text}")
                response = "".join(self.session.handle_stream(user_text))
                print(f"{self.settings.assistant_name}: {response}")
                self.speak(response)
            except Exception as exc:
                print(f"Voice error: {exc}")
                log_action("voice_loop", "failed", error=str(exc))
