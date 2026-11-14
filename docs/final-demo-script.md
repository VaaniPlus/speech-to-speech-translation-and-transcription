# Final demo script

This repeatable 6–8 minute walkthrough demonstrates typed text and speech in
both English ↔ Hindi directions. It is for the Windows setup documented in the
[setup guide](windows-setup.md).

## Before the demo

1. Use a clean checkout and follow the Windows setup guide. Activate `.venv`
   in each terminal, then run the default suite:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   python -m pytest
   ```

2. For a real language/speech demo, install the optional ML packages and
   download/cache the selected models before presenting. Follow the
   [real-model smoke-test instructions](model-smoke-test.md); first use can
   require network access, substantial disk space, and extra startup time.
   Keep model caches outside the repository.
3. Use a microphone and speakers in a supported browser. Obtain permission
   before recording; speak only a short demo phrase and do not save or commit
   recordings.
4. In the API terminal, enable real local providers and start the backend:

   ```powershell
   $env:PROVIDER_MODE = "real"
   $env:DEVICE = "cpu"
   $env:STT_COMPUTE_TYPE = "int8"
   $env:MODEL_CACHE_DIR = "$env:LOCALAPPDATA\VaaniPlus\models"
   $env:HF_HOME = $env:MODEL_CACHE_DIR
   New-Item -ItemType Directory -Force $env:MODEL_CACHE_DIR | Out-Null
   python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
   ```

5. In a second repository-root terminal, serve the frontend:

   ```powershell
   python -m http.server 5500 --directory frontend
   ```

   Open `http://localhost:5500`. Confirm that
   `http://127.0.0.1:8000/api/health` returns `{"status":"ok"}`.

## Walkthrough

1. **Introduce the scope (about 30 seconds).** Explain that the app supports
   English and Hindi, uses local providers for real inference, and does not
   claim perfect translation or speech quality.
2. **English → Hindi, typed (about 1 minute).** Select **English to Hindi**,
   enter `Ravi has 3 books.`, and select **Translate text**. Show the separate
   source and translated-text blocks. The reviewed expected example is in the
   [demo evaluation set](../data/evaluation/translation_transcription_demo.json);
   model wording can vary.
3. **Hindi → English, typed (about 1 minute).** Select **Hindi to English**,
   enter `अमन के पास 5 आम हैं।`, and select **Translate text**. Show the
   English result and explain that normalization can vary.
4. **English → Hindi, speech (about 1–2 minutes).** Select **English to
   Hindi**, select **Start**, say “Good morning.”, select **Stop**, then
   **Translate recording**. Show the transcript, Hindi translation, and
   generated audio. Use Play/Pause/Replay if audio is available.
5. **Hindi → English, speech (about 1–2 minutes).** Select **Hindi to
   English**, say “नमस्ते, आप कैसे हैं?”, stop, and translate. Show the Hindi
   transcript, English translation, and generated audio.
6. **Close (about 30 seconds).** Point out that recordings are sent only after
   submission, mention model/hardware-dependent latency and quality, and stop
   both local servers with Ctrl+C.

## Fallback and troubleshooting

- The default `PROVIDER_MODE=mock` is only for demonstrating the UI/API flow.
  Its transcript and translation are placeholders and its audio is not
  playable speech. Label mock output clearly; it does not satisfy a real
  translation or speech-quality demo.
- If real-model setup or a device fails, use the
  [troubleshooting guide](windows-setup.md#common-issues). Do not spend the
  presentation downloading models or claim a failed stage succeeded.
- For a repeatable checklist, see [demo-checklist.md](demo-checklist.md).
