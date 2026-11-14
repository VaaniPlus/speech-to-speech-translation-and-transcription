# Demo checklist

Use this checklist for the S1 requirements review and later release demos.
Run the product on a clean local checkout and record only observable pass/fail
results. Mocked providers are valid for UI/API checks, but real-model outputs
must be labeled as such.

## Pre-demo setup

- [ ] Repository and environment setup instructions have been reviewed.
- [ ] The backend starts successfully and API documentation is reachable.
- [ ] The frontend loads on a supported desktop browser.
- [ ] Automated tests run without model downloads or GPU access.
- [ ] Browser is opened at `http://localhost:5500` or
  `http://127.0.0.1:5500`; direct `file://` access is not supported.
- [ ] Microphone permission is reset before testing the permission flow.

## Core text pipeline

### Typed-text UI setup

1. From the repository root, activate `.venv` and start the mock backend with
   `python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000`.
2. In another repository-root terminal, serve the frontend with
   `python -m http.server 5500 --directory frontend`, then open
   `http://localhost:5500`.
3. Keep the browser developer tools Network panel open for API checks.

- [ ] Select `en-to-hi`, enter a short English phrase, and click **Translate text**.
- [ ] Verify the request is `POST /api/translate`, the source block, Hindi result
  block, loading label, and success status are all visible as appropriate.
- [ ] Select `hi-to-en`, enter a short Hindi phrase, and click **Translate text**.
- [ ] Verify the source block and English result block show the correct entered
  text and response.
- [ ] Enter whitespace-only text and verify the button remains disabled or that
  submitting shows useful validation.
- [ ] Change direction while a translation request is in progress and verify the
  old request cannot replace the new direction or leave the button stuck loading.
- [ ] Click rapidly while a request is pending and verify the loading state remains
  stable and only the newest result is displayed.
- [ ] Submit repeatedly while the request is active and verify the request is
  guarded against duplicate submissions.
- [ ] Select **Reset** during a pending text request and verify its late response
  cannot restore the cleared result.
- [ ] Enable network throttling or use a cold model load and verify the loading
  state remains visible while a slower response is pending.
- [ ] Stop the backend or configure a provider failure, then repeat the request.
  Verify the safe error message appears without a traceback and the button resets.
- [ ] Submit an invalid direction through the API and verify a useful 4xx response.

The mock providers are intended for repeatable UI/API checks. Any output from
real model weights is a separate manual verification and must be labeled as such.

## Speech pipeline

- [ ] Grant microphone permission and record a short English utterance.
- [ ] Stop the recording, select **Translate recording**, and verify the
  `POST /api/speech-translate` request sends `en-to-hi`.
- [ ] In mock mode, verify the placeholder transcript and translation appear
  in the result blocks and the UI handles the non-playable mock audio without
  claiming it is speech.
- [ ] Grant/reset permission and record a short Hindi utterance.
- [ ] Stop the recording, select **Translate recording**, and verify the
  `POST /api/speech-translate` request sends `hi-to-en`.
- [ ] Verify the placeholder transcript and translation appear in the result
  blocks; do not expect playable audio in mock mode.
- [ ] For playable synthesized speech and Play/Pause/Replay checks, run the
  [optional real-model smoke test](model-smoke-test.md); do not apply these
  checks to mock audio.
- [ ] Replace a successful audio result with a new recording/result and verify
  playback stops and the previous audio resource is released.
- [ ] Simulate an unsupported or failed audio response and verify a useful
  playback error is displayed.
- [ ] Deny microphone permission and verify clear recovery guidance.
- [ ] Send an empty or malformed audio file to `POST /api/speech-translate` and
  verify the API returns a validation error without a traceback.
- [ ] Reset while audio is active and verify playback stops and visible state
  clears.
- [ ] Reset while speech processing is pending and verify the recording,
  transcript, translation, errors, and late response are cleared.
- [ ] Verify a second speech submission cannot start while the first is active.
- [ ] Retry after a recoverable failure and verify stale results are not
  retained.

## Error and accessibility checks

- [ ] STT, translation, and TTS failures show separate, recoverable messages
  in test configuration.
- [ ] Errors do not expose Python tracebacks or private local paths.
- [ ] All controls have visible labels and keyboard focus is usable.
- [ ] Use Tab and Shift+Tab to reach the direction selector, recording and
  translation actions, text field, Reset, and audio controls; verify the focus
  indicator is visible and the focused action can be activated with Enter or
  Space.
- [ ] Verify loading, success, recording, and error states use different
  visual treatments and are announced by the status area.
- [ ] Verify the source transcript and translation remain in separate labeled
  result blocks.
- [ ] At desktop and tablet widths, verify the workspace is readable without
  squeezed controls or horizontal scrolling.
- [ ] Fast repeated submissions do not overwrite an earlier or later result.

## Instructor-facing review

- [ ] Both supported directions are identified explicitly.
- [ ] Typed-text fallback is demonstrated.
- [ ] Speech, translation, and audio stages are explained as replaceable
  provider boundaries.
- [ ] The scope explicitly excludes unsupported languages and cloud features.
- [ ] Fake-provider tests are distinguished from real model demonstrations.
- [ ] Known limitations and setup steps are summarized.
- [ ] The presenter states that the demo does not claim perfect translation
  quality.

See [requirements.md](requirements.md) for the complete functional,
non-functional, journey, and acceptance criteria.
