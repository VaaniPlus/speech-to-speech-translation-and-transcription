# Browser UI user guide

For a clean setup, model configuration, and troubleshooting, see the
[Windows setup guide](../docs/windows-setup.md). With the repository virtual
environment activated, start the backend from the repository root in one
terminal:

```powershell
python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

In another terminal, serve the frontend and open the allowed local origin:

```powershell
python -m http.server 5500 --directory frontend
```

Open `http://localhost:5500` in a modern browser. Do not open `index.html`
directly: the API rejects opaque `Origin: null` requests. The UI provides an
English ↔ Hindi typed-text and speech translation workspace. Microphone capture
starts only after selecting Start and granting browser permission. Select Stop
to finish; the captured audio is
kept in browser memory and microphone tracks are released. Permission denial
and unsupported-browser cases show recovery guidance. Capture requires a
secure context; for this local app, use the loopback origin above. After
recording, select **Translate recording** to send the audio and current
direction to the local
`POST /api/speech-translate` endpoint. Processing progress and safe API/network
errors are shown in the workspace; the captured clip remains available to
retry. The source transcript and translated text are displayed in separate
result blocks. Audio is sent only after this explicit action and is not stored
by the frontend. The generated audio response is played from a browser object
URL using the response's declared audio content type. The result panel provides
play/pause and replay controls, and reports unsupported or failed playback.
Audio URLs are revoked when a new translation replaces the result, the
direction changes, or the page is hidden/left. Capture is cleared when the
direction changes or the page is hidden/left. Select **Reset** to cancel an
active request, clear the typed text, recording, transcript, translation, and
errors, and stop audio playback. Submitting while another request is active is
guarded against duplicates. Fetch requests are aborted where the browser's
`AbortController` supports it; request IDs also prevent late responses from
replacing newer or reset results.

Controls have visible text labels and keyboard focus indicators. Loading,
success, recording, and error messages are announced in the workspace status
area and use distinct visual treatments.

## Data handling and limitations

Audio stays in browser memory until **Translate recording** is selected, then
is submitted to the local API. The backend removes temporary STT files after
inference, including failure paths, and does not log raw audio or full
transcripts by default. Mock mode makes no external model calls. Real providers
run locally, but may download model files from configured hosting sources on
first use. The application has no user accounts or cloud recording library;
do not use sensitive recordings for demos.

The supported language pair is English ↔ Hindi. With the default
`PROVIDER_MODE=mock`, transcript and translation values are placeholders and
the generated audio is not playable speech; mock mode only demonstrates the
workflow. Real-model quality and latency depend on the selected models, input,
and hardware. This demo is not a scientific benchmark. See the [API
documentation](../docs/api.md) for request formats, limits, and errors.
