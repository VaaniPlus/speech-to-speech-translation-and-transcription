# Optional local-model speech smoke test

This manual test is separate from `python -m pytest`. It runs the configured
real STT, translation, and TTS providers through the browser and may download
large model weights on first use. Run it only in an approved environment with
enough disk space and permission to download/cache the selected models. Mock
provider output is not real speech and must not be recorded as a model result.

## Prerequisites

- Python 3.11 and the repository virtual environment are set up.
- A microphone and a supported browser are available. Serve the frontend at
  `http://localhost:5500` or `http://127.0.0.1:5500`; these are the only
  development CORS origins allowed by the API.
- The Windows eSpeak NG runtime required by Kokoro is installed. See
  [TTS model setup](tts-model-selection.md#windows-installation) for the
  project-specific setup notes.
- Model cache storage is outside the Git working tree.

The optional model packages are listed in `requirements-ml.txt`. Install them
only in the environment intended for real inference:

```powershell
python -m pip install -r requirements-ml.txt
```

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
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Keep this API process running. Model providers load lazily, so the first
request for a direction can include model initialization and may take much
longer than subsequent requests. The browser shows the request's processing
state during that time. Do not start duplicate requests while waiting.

In a second PowerShell window from the repository root, serve the frontend:

```powershell
python -m http.server 5500 --directory frontend
```

Open `http://localhost:5500` in the browser. Confirm the API responds at
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
