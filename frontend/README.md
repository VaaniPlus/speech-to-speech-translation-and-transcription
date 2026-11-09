# Frontend

Open `index.html` in a modern browser to view the responsive English ↔ Hindi
translation workspace. Microphone capture starts only after selecting Start
and granting browser permission. Select Stop to finish; the captured audio is
kept in browser memory and microphone tracks are released. Permission denial
and unsupported-browser cases show recovery guidance. Capture requires a
secure context, such as HTTPS or localhost. After recording, select **Translate
recording** to send the audio and current direction to the local
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
