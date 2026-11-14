<div align="center">

# Speech-to-Speech Translation and Transcription

### Local-first speech translation and transcription for English and Hindi

![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)
![Language pair](https://img.shields.io/badge/Language-English%20%E2%86%94%20Hindi-4C8EDA)
![Local-first](https://img.shields.io/badge/Processing-Local--first-2E8B57)

[Overview](#scope) · [How it works](docs/architecture.md) · [Setup](#getting-started) · [API docs](docs/api.md)

</div>

---

A browser-based application that accepts microphone audio or typed text and
translates in two directions: English → Hindi and Hindi → English. The browser
displays the source transcript and translated text and can play generated
target-language audio.

## Scope

This project intentionally supports English and Hindi only. It does not
include other languages, multi-party calls, user accounts, cloud
deployment, or voice cloning. Audio and text are intended to stay local;
do not send them to external services unless the team explicitly documents
and approves that integration.

## Repository layout

- `backend/` — FastAPI application, provider boundaries, service logic,
  schemas, and backend tests.
- `frontend/` — browser UI, styles, and client-side interaction code.
- `docs/` — requirements, architecture, API, testing, and demonstration
  guidance. See [requirements and acceptance tests](docs/requirements.md)
  and [architecture and provider boundaries](docs/architecture.md).
- `scripts/` — local development and Windows setup helpers.
- `IMPLEMENTATION.md` — the Scrum implementation contract and backlog
  for the full project.

## Getting started

The repository is designed to work on Windows with Python 3.11.
For a complete clean-clone walkthrough, real model setup, GPU fallback, and
troubleshooting, see the [Windows setup guide](docs/windows-setup.md).

```powershell
git clone https://github.com/VaaniPlus/speech-to-speech-translation-and-transcription.git
cd speech-to-speech-translation-and-transcription
powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1
.\.venv\Scripts\Activate.ps1
python -m pytest
```

`setup_windows.ps1` requires Python 3.11, creates `.venv`, and installs the
runtime and test dependencies. Heavy STT, translation, and TTS packages are
listed in `requirements-ml.txt`; they are not installed during normal setup and
should only be installed when testing or implementing a real model adapter.

### Configure the environment

The application works with mock providers by default. To customize settings,
copy the example environment file:

```powershell
Copy-Item .env.example .env
```

Configuration includes the API host and port, provider mode, model IDs, cache
directory, device, compute type, log level, and maximum upload size. `.env` is
git-ignored. `PROVIDER_TIMEOUT_SECONDS` sets the per-provider-call deadline
(default: 120 seconds). Invalid settings are reported with the setting name at
startup. See [.env.example](.env.example) for all available variables.

### Start the API

```powershell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Then open:

- Health check: <http://127.0.0.1:8000/api/health>
- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

Startup does not download speech models. The default `PROVIDER_MODE=mock` uses
deterministic fake providers, so the API and UI can be developed without a
GPU, network download, or real model package. Real-provider mode is intended
only after its model adapter is configured and dependencies are installed.

### Local logs

The API writes one JSON log event per line to standard error, visible in the
terminal where Uvicorn is running. Events include request IDs and separate
STT, translation, and TTS durations and outcomes. Raw audio and full transcript
or translation text are not logged by default. To retain logs locally in
PowerShell, redirect standard error to an ignored file:

```powershell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 2> .\vaani-api.log
```

### Open the browser UI

Serve the frontend locally and open it from a loopback origin:

```powershell
python -m http.server 5500 --directory frontend
```

Open <http://localhost:5500> in a desktop browser while the API is running.
The typed-text UI is connected to `POST /api/translate` for English → Hindi and
Hindi → English requests; loading and error states are shown in the browser.
Microphone capture starts only after selecting Start and granting browser
permission. After stopping, select **Translate recording** to send the captured
audio and selected direction to the local speech translation API. The source
transcript and translated text are shown separately, and the generated
target-language audio can be played from the result panel. Use **Reset** to
clear the current input and result or cancel in-flight processing. The
supported loopback origins provide the secure context required for microphone
access.

### Run tests

```powershell
python -m pytest
```

The default suite uses fake providers and does not download model weights. See
[testing](docs/testing.md) for the focused speech integration test and
[optional real-model smoke test](docs/model-smoke-test.md).

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

## Sprint checklists

Track each Scrum item here. The Scrum IDs, Jira keys, acceptance criteria,
and release checkpoint steps are maintained in
[IMPLEMENTATION.md](IMPLEMENTATION.md).

### Sprint 1 — Foundation, requirements, and project skeleton

- [x] S1-01 / AMTT-1 — Create repository and project baseline.
- [x] S1-02 / AMTT-2 — Create Jira backlog and four sprints.
- [x] S1-03 / AMTT-3 — Finalize requirements and acceptance tests.
- [x] S1-04 / AMTT-4 — Document architecture and provider boundaries.
- [x] S1-05 / AMTT-5 — Set up Python environment and dependencies.
- [x] S1-06 / AMTT-6 — Add environment configuration.
- [x] S1-07 / AMTT-7 — Implement FastAPI application entry point.
- [x] S1-08 / AMTT-8 — Implement health endpoint and basic API tests.
- [x] S1-09 / AMTT-9 — Build initial browser UI shell.
- [x] S1-10 / AMTT-10 — Establish Git branching, PR, and review rules.

Sprint 1 Scrum items are complete. The `v0.1-foundation` release checkpoint
remains pending until its tag is created and all four members confirm they
can pull and run the skeleton.

### Sprint 2 — Working text pipeline and model adapters

- [x] S2-01 / AMTT-11 — Define request and response schemas.
- [x] S2-02 / AMTT-12 — Define STT, translation, and TTS provider interfaces.
- [x] S2-03 / AMTT-13 — Implement fake providers for development.
- [x] S2-04 / AMTT-14 — Verify and document the Windows-compatible STT model. See [STT model selection](docs/stt-model-selection.md).
- [x] S2-05 / AMTT-15 — Implement the faster-whisper STT adapter.
- [x] S2-06 / AMTT-16 — Verify and document the English↔Hindi translation model. See [translation model selection](docs/translation-model-selection.md).
- [x] S2-07 / AMTT-17 — Implement the translation provider adapter.
- [x] S2-08 / AMTT-18 — Implement the text translation service.
- [x] S2-09 / AMTT-19 — Add `POST /api/translate` endpoint.
- [x] S2-10 / AMTT-20 — Connect the typed-text UI to the translation API.

Sprint 2 release checkpoint: `v0.2-text-translation`.

### Sprint 3 — Speech input and translated speech output

- [x] S3-01 / AMTT-21 — Verify Windows-compatible English/Hindi TTS options. See [TTS model selection](docs/tts-model-selection.md).
- [ ] S3-02 / AMTT-22 — Implement TTS provider adapter.
- [ ] S3-03 / AMTT-23 — Add safe audio input validation and utilities.
- [ ] S3-04 / AMTT-24 — Add `POST /api/speech-to-text` endpoint.
- [ ] S3-05 / AMTT-25 — Add `POST /api/speech-translate` orchestration endpoint.
- [ ] S3-06 / AMTT-26 — Implement browser microphone permission and capture.
- [ ] S3-07 / AMTT-27 — Upload captured audio and show source transcript.
- [ ] S3-08 / AMTT-28 — Play generated translated audio.
- [ ] S3-09 / AMTT-29 — Add cancellation, reset, and duplicate-request protection.
- [ ] S3-10 / AMTT-30 — Run speech pipeline integration tests.

Sprint 3 release checkpoint: `v0.3-speech-pipeline`.

### Sprint 4 — Quality, reliability, documentation, and final demo

- [ ] S4-01 / AMTT-31 — Improve end-to-end UI states and accessibility.
- [ ] S4-02 / AMTT-32 — Add request timeout and model failure handling.
- [ ] S4-03 / AMTT-33 — Add structured logging and timing metrics.
- [ ] S4-04 / AMTT-34 — Add translation and transcription evaluation set.
- [ ] S4-05 / AMTT-35 — Add performance and memory benchmark script.
- [ ] S4-06 / AMTT-36 — Harden input and temporary-file handling.
- [ ] S4-07 / AMTT-37 — Write Windows setup and troubleshooting guide.
- [ ] S4-08 / AMTT-38 — Complete API and user documentation.
- [ ] S4-09 / AMTT-39 — Run full regression and acceptance checklist.
- [ ] S4-10 / AMTT-40 — Prepare final demo, release tag, and handoff.

Sprint 4 release checkpoint: `v1.0.0`.
