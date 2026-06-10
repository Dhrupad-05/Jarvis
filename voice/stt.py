from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.audit import log_action
from core.config import Settings
from core.exceptions import VoiceError


@dataclass(slots=True)
class WhisperTranscriber:
    settings: Settings
    _model: Any = field(default=None, init=False, repr=False)

    def _load_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise VoiceError("Speech-to-text requires 'faster-whisper'.") from exc
        self._model = WhisperModel(self.settings.whisper_model_size, device="cpu", compute_type="int8")
        return self._model

    def transcribe(self, audio_path: Path) -> str:
        model = self._load_model()
        segments, info = model.transcribe(str(audio_path), vad_filter=True)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        log_action("voice_transcription", "success", language=getattr(info, "language", None), chars=len(text))
        return text
