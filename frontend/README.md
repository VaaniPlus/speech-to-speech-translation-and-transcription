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
by the frontend. Capture is cleared when the direction changes or the page is
hidden/left. Translated-audio playback is a separate feature.
