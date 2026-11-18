# Optional local-model speech smoke test

This manual test is separate from `uv run --project backend pytest`. It runs the configured
real STT, translation, and TTS providers through the browser and may download
large model weights on first use. Run it only in an approved environment with
enough disk space and permission to download/cache the selected models. Mock
provider output is not real speech and must not be recorded as a model result.

## Prerequisites

- uv and the backend project are set up with `uv sync --project backend --extra ml`.
- Node.js and npm are installed. A microphone and a supported browser are
  available. Run the Vite frontend at `http://127.0.0.1:5173`.
- The Windows eSpeak NG runtime required by Kokoro is installed. See
  [TTS model setup](tts-model-selection.md#windows-installation) for the
  project-specific setup notes.
- Model cache storage is outside the Git working tree.

## Run the real providers

In the PowerShell window that will start the backend, set real mode and an
external cache path. CPU mode is the conservative first run; it does not
require CUDA libraries. The directional model IDs can be overridden if an
approved local model mirror is being used.

```powershell
$env:PROVIDER_MODE = "real"
$env:DEVICE = "cpu"
$env:STT_COMPUTE_TYPE = "int8"
$env:MODEL_CACHE_DIR = "$env:LOCALAPPDATA\VaaniPlus\models"
New-Item -ItemType Directory -Force $env:MODEL_CACHE_DIR | Out-Null
uv run --project backend --directory backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Keep this API process running. Model providers load lazily, so the first
request for a direction can include model initialization and may take much
longer than subsequent requests. The browser shows the request's processing
state during that time. Do not start duplicate requests while waiting.

In a second PowerShell window, start the Vite frontend:

```powershell
Set-Location .\frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173` in the browser. Confirm the API responds at
`http://127.0.0.1:8000/api/health`, then test each direction:

1. Select **English to Hindi**, grant microphone access, record a short,
   clearly spoken English greeting, and select Stop.
2. Select **Translate recording** once. Wait for processing to finish, then
   check the source transcript, Hindi translation, and generated audio.
3. Use Play, Pause, and Replay. Listen for intelligible output and note any
   pronunciation or audio-format issues.
4. Repeat with **Hindi to English** and a short Hindi greeting.
5. Record whether each result is reasonable; do not treat these suggested
   phrases as expected exact translations.

The UI records no model benchmark. For each direction, note the date,
`STT_MODEL_ID`, directional translation model ID, TTS model ID/voice, selected
device, whether weights were already cached, approximate first-request and
warm-request times, transcript, translated text, and playback/quality
observations. Clearly distinguish measured values from estimates. Do not commit
recordings, generated audio, model files, or private transcripts.

To return the current shell to mock mode after stopping the API:

```powershell
Remove-Item Env:PROVIDER_MODE, Env:DEVICE, Env:STT_COMPUTE_TYPE, Env:MODEL_CACHE_DIR `
  -ErrorAction SilentlyContinue
```

This only clears overrides in the current PowerShell process. It does not
remove cached weights.
