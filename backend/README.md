# Backend

The backend is a standalone Python 3.11 uv project. Install uv, then sync the
API and test dependencies from this directory:

```powershell
uv sync
```

Start the API and run its tests from `backend/`:

```powershell
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
uv run pytest
```

Mock providers are the default and do not load model packages or download
weights. To install optional local inference dependencies, sync the `ml` extra:

```powershell
uv sync --extra ml
```

Run the optional live microphone transcription example with a CUDA-capable
Windows environment:

```powershell
uv run python scripts/stage1_speech_to_text_live.py
```

Real providers may download model weights on first use. Configure the backend
with environment variables or `backend/.env`. To create the local configuration:

```powershell
Copy-Item .env.example .env
```

For Windows model setup and provider options, see the
[Windows setup guide](../docs/windows-setup.md).
