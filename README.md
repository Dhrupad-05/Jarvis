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
- `/memory stats`
- `/memory list`
- `/memory search <query>`
- `/memory delete <id>`
- `/memory export`
- `/reset`
- `/exit`

Memory commands can also be used naturally:

```powershell
python app.py --once "remember My test phrase is banana rocket 947"
python app.py --once "What is my test phrase?"
```

Coding assistant commands:

```powershell
python app.py --once "analyze repo ."
python app.py --once "explain error Traceback TypeError: bad operand"
python app.py --once "coding task refactor the router"
```

## Architecture

- `core`: settings, logging, constants, exceptions
- `brain`: Ollama client and session orchestration
- `router`: intent classification and dispatch
- `tools`: pluggable tool registry with placeholder capabilities
- `voice`: push-to-talk microphone, faster-whisper STT, Piper TTS
- `security`: permission levels and confirmation policy
- `memory`: SQLite-backed durable memories with bounded retrieval
- `coding`: repository indexing, error analysis, and coding context helpers
- `modes`: configuration-driven assistant behavior modes
- `shared`: DTOs and utilities
