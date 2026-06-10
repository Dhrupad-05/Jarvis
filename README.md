# Local AI Assistant

Local-first personal AI assistant foundation for Windows + Ollama.

## Run

```powershell
python app.py
```

Default model: `qwen3:14b` via Ollama at `http://localhost:11434`.

Voice mode is push-to-talk and optional:

```powershell
python app.py --voice
```

Set `ENABLE_VOICE=true` and configure `PIPER_VOICE` in `.env` for full STT/TTS. Install optional extras as needed:

```powershell
python -m pip install -e ".[voice,browser]"
python -m playwright install chromium
```

## Commands

- `/mode study`
- `/mode productivity`
- `/mode research`
- `/mode interview`
- `/modes`
- `/reset`
- `/exit`

## Architecture

- `core`: settings, logging, constants, exceptions
- `brain`: Ollama client and session orchestration
- `router`: intent classification and dispatch
- `tools`: pluggable tool registry with placeholder capabilities
- `voice`: push-to-talk microphone, faster-whisper STT, Piper TTS
- `security`: permission levels and confirmation policy
- `modes`: configuration-driven assistant behavior modes
- `shared`: DTOs and utilities
