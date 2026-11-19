# Browser UI user guide

For a clean setup, model configuration, and troubleshooting, see the
[Windows setup guide](../docs/windows-setup.md). Start the backend from the
repository root in one terminal:

```powershell
uv run --project backend --directory backend uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In another terminal, install the frontend dependencies once and start Vite:

```powershell
Set-Location .\frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173` in a modern browser. Vite proxies `/api` requests
to the local backend at `127.0.0.1:8000`. The UI provides an English ↔ Hindi
typed-text and speech translation workspace. After typed translation, the
translated text is sent to the local `POST /api/text-to-speech` endpoint and
the returned audio is available through the Play and Replay controls. The
**Try demo text** dropdown loads sample phrases for the selected direction.
The first screen is account sign-in; use **Create account** for a new local
account. PostgreSQL must be running with `docker compose up -d postgres` from
the repository root. Successful sign-in opens the translation workspace for
the current browser tab, and **Sign out** returns to the auth screen.
The dashboard lists the signed-in user's five most recent typed or speech
conversions, saved in the local PostgreSQL database.
Microphone capture starts only
after selecting Start and granting browser permission. Select Stop to finish;
the captured audio is kept in browser memory and microphone tracks are
released. Permission denial and unsupported-browser cases show recovery
guidance. Capture requires a secure context; for this local app, use the
loopback origin above. After recording, select **Translate recording** to send
the audio and current direction to the local `POST /api/speech-translate`
endpoint. Processing progress and safe API/network errors are shown in the
workspace; the captured clip remains available to retry. The source transcript
and translated text are displayed in separate result blocks. Audio is sent
only after this explicit action and is not stored by the frontend. The
generated audio response is played from a browser object URL using the
response's declared audio content type. The result panel provides play/pause
and replay controls, and reports unsupported or failed playback. Audio URLs
are revoked when a new translation replaces the result, the direction changes,
or the page is left. Capture is cleared when the direction changes, the page
is hidden, or the page is left. Switching to another browser tab no longer
cancels translation requests or clears their results. Select **Reset** to
cancel an active request, clear the typed text, recording, transcript,
translation, and errors, and stop audio playback. Submitting while another
request is active is guarded against duplicates. Fetch requests are aborted
where the browser's `AbortController` supports it; request IDs also prevent
late responses from replacing newer or reset results.

Controls have visible text labels and keyboard focus indicators. Loading,
success, recording, and error messages are announced in the workspace status
area and use distinct visual treatments.

## Data handling and limitations

Audio stays in browser memory until **Translate recording** is selected, then
is submitted to the local API. The backend removes temporary STT files after
inference, including failure paths, and does not log raw audio or full
transcripts by default. Mock mode makes no external model calls. Real providers
run locally, but may download model files from configured hosting sources on
first use. Accounts are stored in the local PostgreSQL database; the
application has no cloud recording library. Do not use sensitive recordings
for demos.

The supported language pair is English ↔ Hindi. With the default
`PROVIDER_MODE=mock`, transcript and translation values are placeholders and
the generated audio is not playable speech; mock mode only demonstrates the
workflow. Real-model quality and latency depend on the selected models, input,
and hardware. This demo is not a scientific benchmark. See the [API
documentation](../docs/api.md) for request formats, limits, and errors.
