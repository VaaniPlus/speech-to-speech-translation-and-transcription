<div align="center">

# VaaniPlus

### Speech translation and transcription for English and Hindi

### Translate speech. Preserve meaning. Keep it local.

<p>
<img alt="Frontend" src="https://img.shields.io/badge/FRONTEND-Vite%20%2B%20TypeScript-646cff?style=for-the-badge&logo=vite&logoColor=white">
<img alt="Backend" src="https://img.shields.io/badge/BACKEND-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white">
<img alt="Server" src="https://img.shields.io/badge/SERVER-Uvicorn-2f855a?style=for-the-badge">
<img alt="Runtime" src="https://img.shields.io/badge/RUNTIME-uv-7c3aed?style=for-the-badge">
</p>
<p>
<img alt="Speech to text" src="https://img.shields.io/badge/SPEECH_TO_TEXT-Faster--Whisper-2563EB?style=for-the-badge">
<img alt="Translation" src="https://img.shields.io/badge/TRANSLATION-MarianMT%20(default)-7C3AED?style=for-the-badge">
<img alt="Text to speech" src="https://img.shields.io/badge/TEXT_TO_SPEECH-Kokoro-EC4899?style=for-the-badge">
</p>
<p>
<img alt="Models" src="https://img.shields.io/badge/MODELS-Hugging%20Face-facc15?style=for-the-badge&logo=huggingface&logoColor=black">
</p>

VaaniPlus is a local-first browser application for English ↔ Hindi speech
translation and transcription. Its pipeline is **speech-to-text → text
translation → text-to-speech**. The Vite + vanilla TypeScript frontend provides
microphone capture, typed-text input, result display, and audio playback. The
FastAPI backend coordinates replaceable Faster-Whisper, MarianMT, and Kokoro
providers.

[Overview](#scope) · [User guide](frontend/README.md) · [How it works](docs/architecture.md) · [Setup](#getting-started) · [API docs](docs/api.md) · [Final demo](docs/final-demo-script.md) · [Handoff](docs/final-handoff.md)

</div>

---

## Scope

This project intentionally supports English and Hindi only. It does not
include other languages, multi-party calls, user accounts, cloud
deployment, or voice cloning. Audio and text are intended to stay local;
do not send them to external services unless the team explicitly documents
and approves that integration.

## Project structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes
│   │   ├── core/         # Configuration and logging
│   │   ├── providers/    # Faster-Whisper, MarianMT, Kokoro
│   │   ├── schemas/      # Request and response models
│   │   ├── services/     # Speech, translation, and synthesis workflows
│   │   ├── utils/
│   │   └── main.py
│   ├── scripts/          # Local evaluation and benchmarks
│   ├── tests/
│   ├── pyproject.toml
│   └── uv.lock
├── frontend/
│   ├── src/main.ts       # Vanilla TypeScript UI behavior
│   ├── index.html
│   ├── styles.css
│   ├── package.json
│   └── vite.config.ts
├── data/                 # Evaluation datasets
├── docs/                 # Architecture, API, setup, and demo guides
├── scripts/              # Optional development helpers
└── README.md
```

See the [backend setup](backend/README.md), [frontend setup](frontend/README.md),
[requirements](docs/requirements.md), and
[architecture guide](docs/architecture.md) for details.

## Getting started

Start the backend and frontend in two separate PowerShell terminals from the
repository root. `uv run` prepares the backend environment automatically. On
the first frontend run, install its dependencies once with `npm ci`.

### Terminal 1 — Backend

```powershell
uv run --project backend --directory backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Terminal 2 — Frontend

```powershell
Set-Location .\frontend
# First run only:
npm ci
npm run dev
```

Open <http://127.0.0.1:5173>. The frontend communicates with the API through
Vite's `/api` proxy. For optional real-model configuration and troubleshooting,
see the [Windows setup guide](docs/windows-setup.md).

### Translation modes

Without a local `.env`, the backend uses mock providers; mock results are
placeholders, not real translations or speech. To enable local model inference,
copy the example configuration and install the optional model dependencies
once:

```powershell
Copy-Item backend/.env.example backend/.env
uv sync --project backend --extra ml
```

The example selects real providers and **MarianMT** for typed English ↔ Hindi
translation. Its model downloads on the first translation request. See the
[translation model guide](docs/translation-model-selection.md) for model and
Windows notes.

### Run tests

```powershell
uv run --project backend pytest
```

The default suite uses fake providers and does not download model weights. See
[testing](docs/testing.md) for the focused speech integration test and
[optional real-model smoke test](docs/model-smoke-test.md).

### Latest local validation (2026-11-18)

- `uv run --project backend pytest`: 128 passed, 1 skipped. The skip is the
  optional real Faster-Whisper test, which needs model inference and a recording.
- A real MarianMT API request returned Hindi, and Kokoro generated a valid Hindi
  WAV file.
- Mock providers remain workflow placeholders. Physical microphone capture and
  real STT inference were not validated in this run.

This smoke check is not a translation-quality benchmark. See the
[demo checklist](docs/demo-checklist.md) for workflow validation.

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
