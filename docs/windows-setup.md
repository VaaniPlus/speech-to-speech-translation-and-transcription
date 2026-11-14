# Windows setup and troubleshooting

This project targets 64-bit Windows and Python 3.11. The regular setup uses
mock providers, so it does not install machine-learning packages or download
model weights. Real model setup is optional and described below.

## Clean clone and test

Install Git and Python 3.11, then open PowerShell:

```powershell
git clone https://github.com/VaaniPlus/speech-to-speech-translation-and-transcription.git
Set-Location .\speech-to-speech-translation-and-transcription
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
.\.venv\Scripts\Activate.ps1
python --version
python -m pytest
```

The version command should report Python 3.11. The setup script creates `.venv`
and installs `requirements-dev.txt` (runtime and test dependencies). The test
suite uses fake providers and does not need a GPU, model packages, or model
downloads.

If PowerShell blocks virtual-environment activation, run commands with the
environment's interpreter directly, for example:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## Start the application

In the first PowerShell window, from the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In a second window, also from the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
python -m http.server 5500 --directory frontend
```

Open <http://localhost:5500>. The API health check is
<http://127.0.0.1:8000/api/health>; interactive API documentation is at
<http://127.0.0.1:8000/docs>. Serve the frontend over one of the documented
loopback origins; opening `frontend/index.html` directly as a `file://` page
is not supported by the CORS policy.

By default, `PROVIDER_MODE=mock` lets you use the UI and API without real
models. To stop either server, press Ctrl+C in its PowerShell window.

## Optional real models and cache

Real providers need optional packages and local model weights. From an
activated environment, install the packages only when you intend to run real
inference:

```powershell
python -m pip install -r requirements-ml.txt
```

This installs Python packages; it does not download the model weights. Real
providers load lazily, and the first request for a stage/direction may download
and cache its selected model. Keep the computer online for that first use and
allow time and disk space for the downloads. Normal setup and API startup do
not download model weights.

In the PowerShell window that will run the backend, explicitly enable real
providers and start with CPU-safe settings:

```powershell
$env:PROVIDER_MODE = "real"
$env:DEVICE = "cpu"
$env:STT_COMPUTE_TYPE = "int8"
```

Model IDs are configured by `STT_MODEL_ID`, `TRANSLATION_EN_HI_MODEL_ID`,
`TRANSLATION_HI_EN_MODEL_ID`, `TTS_EN_MODEL_ID`, and `TTS_HI_MODEL_ID`. The
defaults are the Windows-oriented candidates described in the
[STT](stt-model-selection.md), [translation](translation-model-selection.md),
and [TTS](tts-model-selection.md) selection notes. Check those notes for
licensing and known limitations before distributing model files.

Keep caches outside the Git working tree. `MODEL_CACHE_DIR` is used by the
STT and translation adapters; Hugging Face-backed components such as TTS also
use the Hugging Face cache. Set both locations in the shell that will run the
API:

```powershell
$env:MODEL_CACHE_DIR = "$env:LOCALAPPDATA\VaaniPlus\models"
$env:HF_HOME = $env:MODEL_CACHE_DIR
New-Item -ItemType Directory -Force $env:MODEL_CACHE_DIR | Out-Null
```

These process-level variables override `.env` settings for that shell. To
return to defaults, close the shell or remove the variables:

```powershell
Remove-Item Env:MODEL_CACHE_DIR, Env:HF_HOME -ErrorAction SilentlyContinue
```

## Configuration reference

Copy `.env.example` to `.env` to persist application settings locally. `.env`
is ignored by Git; do not put secrets or private data in it.

```powershell
Copy-Item .env.example .env
notepad .env
```

Restart the backend after changing `.env` or its process environment so the
settings are reloaded.

| Variable | Default | Purpose |
|---|---|---|
| `PROVIDER_MODE` | `mock` | `mock` uses deterministic fakes; set to `real` to enable local model providers. |
| `STT_MODEL_ID` | `Systran/faster-whisper-small` | Faster-Whisper model ID. |
| `STT_COMPUTE_TYPE` | `auto` | CTranslate2 precision/quantization setting; `int8` is a practical CPU starting point. |
| `TRANSLATION_EN_HI_MODEL_ID` | `ai4bharat/indictrans2-en-indic-dist-200M` | English-to-Hindi checkpoint. |
| `TRANSLATION_HI_EN_MODEL_ID` | `ai4bharat/indictrans2-indic-en-dist-200M` | Hindi-to-English checkpoint. |
| `TTS_EN_MODEL_ID` / `TTS_HI_MODEL_ID` | `hexgrad/Kokoro-82M` | Kokoro model IDs for each target language. |
| `MODEL_CACHE_DIR` | `models` | Cache path passed to STT and translation providers; use an external path. |
| `HF_HOME` | Hugging Face default | Optional process environment variable for Hugging Face cache location. |
| `DEVICE` | `auto` | `auto`, `cpu`, or `cuda` for STT/translation provider selection. |
| `MAX_UPLOAD_SIZE_BYTES` | `26214400` | Maximum audio upload size (25 MiB). |
| `PROVIDER_TIMEOUT_SECONDS` | `120` | Timeout for each provider call. |
| `HOST` / `PORT` | `127.0.0.1` / `8000` | Validated application settings. The Uvicorn command above explicitly selects its host and port. |
| `LOG_LEVEL` | `INFO` | `CRITICAL`, `ERROR`, `WARNING`, `INFO`, or `DEBUG`. |

The real TTS adapter currently runs on CPU regardless of `DEVICE`. First try
the default `DEVICE=auto`; it allows provider runtimes to select available
hardware but does not guarantee that an installed CUDA stack is compatible.
If GPU initialization fails, use `DEVICE=cpu` and `STT_COMPUTE_TYPE=int8`.
Explicit `DEVICE=cuda` requires a working, compatible CUDA runtime. Faster-
Whisper GPU use depends on CTranslate2-compatible NVIDIA libraries; follow the
STT model notes and verify the installed runtime rather than assuming that a
GPU is usable. The generic `requirements-ml.txt` install does not certify a
CUDA-enabled PyTorch build. For NVIDIA inference, select a PyTorch build that
matches the installed Windows driver/runtime, then check it in the activated
environment:

```powershell
python -c "import torch; print(torch.cuda.is_available())"
```

If it prints `False` or a provider fails to initialize CUDA, use the CPU
settings instead.

## Windows platform compatibility

Do not select a model that requires Apple's MLX runtime. The MLX-Audio candidate
evaluated earlier targets Apple platforms and cannot run on Windows; installing
its Python package does not make its runtime Windows-compatible. Do not select
it or any model that requires an Apple-only runtime. Use the documented
Windows-compatible providers instead. For GPU use, select Windows-compatible
CUDA/PyTorch and CTranslate2 builds; otherwise use the CPU configuration above.

## Common issues

| Symptom | Resolution |
|---|---|
| `py -3.11` is unavailable or setup reports the wrong Python version | Install 64-bit Python 3.11 and verify `py -3.11 --version`; recreate the environment only after checking that no project work is stored in `.venv`. |
| `No module named uvicorn`, `fastapi`, or `pytest` | Activate `.venv` or use `.\.venv\Scripts\python.exe`, then rerun `powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1`. |
| A real provider reports a missing package such as `faster_whisper`, `IndicTransToolkit`, or `kokoro` | Activate `.venv` and install `requirements-ml.txt`. This installs packages, not model weights. |
| First real request is slow, times out, or cannot find a model | Check network access for the first download, free disk space, `MODEL_CACHE_DIR`/`HF_HOME`, and the API terminal logs. The default timeout is 120 seconds; adjust `PROVIDER_TIMEOUT_SECONDS` only if a longer first load is expected. Avoid duplicate requests while a timed-out provider call may still be running. |
| CUDA initialization fails, or the GPU is unsupported | Set `DEVICE=cpu` and `STT_COMPUTE_TYPE=int8`, restart the API, and retry. For GPU use, verify that PyTorch and CTranslate2 match the installed NVIDIA driver/runtime. |
| Kokoro reports an eSpeak or phonemizer error | Install the Windows eSpeak NG runtime described in the [TTS model notes](tts-model-selection.md), then restart PowerShell and the API. |
| Browser reports a CORS error | Run the frontend at `http://localhost:5500` or `http://127.0.0.1:5500` and the API at `127.0.0.1:8000`. Direct `file://` pages and other ports are not allowed. |
| Port 8000 or 5500 is already in use | Stop the existing local server before starting another instance. The documented frontend/API origins use these ports. |

The application logs request IDs, stage timings, and safe error codes to the
API terminal. It does not log raw audio or full transcript/translation text by
default. Real model downloads contact the configured model hosting service;
the default mock setup does not. Do not add recordings, generated speech, model
weights, or private transcripts to the repository.
