<div align="center">

# VaaniPlus

### Speech translation and transcription for English and Hindi

### Translate speech. Preserve meaning. Keep it local.

<p>
<img alt="Frontend" src="https://img.shields.io/badge/FRONTEND-Vite%20%2B%20TypeScript-646cff?style=for-the-badge&logo=vite&logoColor=white">
<img alt="Backend" src="https://img.shields.io/badge/BACKEND-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white">
<img alt="Runtime" src="https://img.shields.io/badge/RUNTIME-uv-7c3aed?style=for-the-badge">
</p>
<p>
<img alt="Speech to text" src="https://img.shields.io/badge/SPEECH_TO_TEXT-Faster--Whisper-2563EB?style=for-the-badge">
<img alt="Translation" src="https://img.shields.io/badge/TRANSLATION-AI4India-FF9933?style=for-the-badge">
<img alt="Text to speech" src="https://img.shields.io/badge/TEXT_TO_SPEECH-Kokoro-EC4899?style=for-the-badge">
</p>
<p>
<img alt="Models" src="https://img.shields.io/badge/MODELS-Hugging%20Face-facc15?style=for-the-badge&logo=huggingface&logoColor=black">
</p>

VaaniPlus is a local-first browser application for English ↔ Hindi speech
translation and transcription. The vanilla TypeScript frontend provides
microphone capture, typed-text input, result display, and audio playback. The
FastAPI backend coordinates replaceable STT, translation, and TTS providers
through a privacy-focused local pipeline.

[Overview](#scope) · [User guide](frontend/README.md) · [How it works](docs/architecture.md) · [Setup](#getting-started) · [API docs](docs/api.md) · [Final demo](docs/final-demo-script.md) · [Handoff](docs/final-handoff.md)

</div>

---

## Scope

This project intentionally supports English and Hindi only. It does not
include other languages, multi-party calls, user accounts, cloud
deployment, or voice cloning. Audio and text are intended to stay local;
do not send them to external services unless the team explicitly documents
and approves that integration.

## Repository layout

- `backend/` — standalone Python project with its own dependencies, FastAPI
  application, provider boundaries, service logic, schemas, and tests. See
  [backend setup](backend/README.md).
- `frontend/` — standalone Vite-powered vanilla TypeScript browser UI and
  styles. See the [frontend setup guide](frontend/README.md).
- `docs/` — requirements, architecture, API, testing, and demonstration
  guidance. See [requirements and acceptance tests](docs/requirements.md)
  and [architecture and provider boundaries](docs/architecture.md). The
  [final demo script](docs/final-demo-script.md) and
  [handoff](docs/final-handoff.md) record release readiness.
- `data/` — evaluation datasets used for local validation.
- `scripts/` — local development and Windows setup helpers.
  Use `scripts/run_dev.ps1` to start both applications.

## Getting started

### Quick start

```powershell
# 1. Set up the backend
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1

# 2. Start the backend
uv run --project backend --directory backend uvicorn app.main:app --host 127.0.0.1 --port 8000

# 3. Start the frontend in a second terminal
Set-Location .\frontend
npm ci
npm run dev
```

Open <http://127.0.0.1:5173>. The frontend communicates with the API through
Vite's `/api` proxy.

The backend and tests use Python 3.11; the Vite frontend requires Node.js and
npm.
For a complete clean-clone walkthrough, real model setup, GPU fallback, and
troubleshooting, see the [Windows setup guide](docs/windows-setup.md).

### 1. Initial Setup and Virtual Environment

```powershell
git clone https://github.com/VaaniPlus/speech-to-speech-translation-and-transcription.git
cd speech-to-speech-translation-and-transcription
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
uv run --project backend pytest
```

`setup_windows.ps1` uses uv to sync the backend project into `backend/.venv`.
To install backend dependencies directly from its folder, see the
[backend setup guide](backend/README.md). Real-model packages are optional;
install them with `uv sync --project backend --extra ml` only when you plan to
run real inference.

### 2. Configure the Environment

Copy the example environment configuration:

```powershell
Copy-Item backend/.env.example backend/.env
```

Key environment options in `.env`:
- `PROVIDER_MODE=real` (configured by `backend/.env.example`): Uses real local neural translation (MarianMT / IndicTrans2). Set to `mock` if you prefer offline deterministic placeholders.
- `DEVICE=cpu`: CPU inference mode (or `cuda` if compatible NVIDIA GPU is available).
- `STT_COMPUTE_TYPE=int8`: 8-bit quantized compute for CPU-friendly STT inference.
- `PROVIDER_TIMEOUT_SECONDS=300`: Timeout for provider calls (allows time for first-time model downloads).
- `MODEL_CACHE_DIR=models`: Directory where model weights are cached.

### 3. Running the Application

Running the application requires **two separate PowerShell terminals** simultaneously:

#### Terminal 1 — Start the Backend API (Port 8000)

```powershell
uv run --project backend --directory backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Verify backend health at: <http://127.0.0.1:8000/api/health>  
Interactive Swagger docs: <http://127.0.0.1:8000/docs>

> **Note on First Run**: The first translation request will automatically download the Helsinki-NLP MarianMT model (~300 MB) from Hugging Face into `models/`. Subsequent translations run entirely locally and return instantly.

#### Terminal 2 — Start the Vite Frontend (Port 5173)

```powershell
Set-Location .\frontend
npm ci
npm run dev
```

#### Terminal 3 / Browser — Open the UI

Open your browser to <http://127.0.0.1:5173>. Vite proxies frontend `/api`
requests to the backend on port 8000.

> **Important**: Do not open `frontend/index.html` directly via `file://`.
> Browser microphone capture requires serving over loopback HTTP.

### 4. Running Tests

```powershell
uv run --project backend pytest
```

The default suite uses fake providers and does not download model weights. See
[testing](docs/testing.md) for the focused speech integration test and
[optional real-model smoke test](docs/model-smoke-test.md).

### Latest Windows acceptance run (2026-11-14)

- `uv run --project backend pytest`: 129 passed, 1 skipped. The skip is the opt-in real
  Faster-Whisper smoke test, which requires a recording and model inference.
- Typed-text and speech workflows passed in both directions with mock
  providers. Speech UI checks used synthetic WAV data; microphone denial was
  simulated by rejecting the browser permission request.
- Provider failure/timeout tests passed (8 targeted cases). Whitespace text
  and empty audio were rejected; API health, Swagger, and OpenAPI returned
  successfully.

Physical microphone capture and real-model inference were not performed.
Mock transcript, translation, and audio output are placeholders, so this run
does not validate language or speech quality. See the
[demo checklist](docs/demo-checklist.md).

## Project workflow

Contributors should work on one short-lived branch per Scrum item, based on
the latest `main`, and open a pull request for each completed item. Never
commit or push directly to shared `main`, and never force-push it. Rebase a
feature branch before publishing if `main` has moved; use GitHub's **Squash and
merge** option to avoid merge commits. A different team member should review
the pull request and approve it before it is merged.

```powershell
git switch main
git pull --ff-only origin main
git switch -c feature/AMTT-<number>-short-description
# Make and test the change, then commit only the relevant files.
git push -u origin feature/AMTT-<number>-short-description
```

Replace the example branch name with the task's Jira key and a short
description. Use the pull request checklist in
[`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md).
Repository administrators should protect `main` by requiring an approving
review and preventing force pushes and branch deletion. This repository's
branch protection must be enabled in GitHub settings by an administrator.
