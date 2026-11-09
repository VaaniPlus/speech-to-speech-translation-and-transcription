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
- [ ] Browser is opened over `localhost` or HTTPS so microphone capture is
  available.
- [ ] Microphone permission is reset before testing the permission flow.

## Core text pipeline

### Typed-text UI setup

1. Start the mock backend from the repository root with
   `python -m uvicorn backend.app.main:app --reload` (Windows users may need
   to activate the virtual environment first).
2. Serve the frontend from the repository root, for example with
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
- [ ] Stop the backend or configure a provider failure, then repeat the request.
  Verify the safe error message appears without a traceback and the button resets.
- [ ] Submit an invalid direction through the API and verify a useful 4xx response.

The mock providers are intended for repeatable UI/API checks. Any output from
real model weights is a separate manual verification and must be labeled as such.

## Speech pipeline

- [ ] Grant microphone permission and record a short English utterance.
- [ ] Stop the recording, select **Translate recording**, and verify the
  `POST /api/speech-translate` request sends `en-to-hi`.
- [ ] Verify progress, English transcript, Hindi
  translation, and playable Hindi audio.
- [ ] Use Play, Pause, and Replay and verify each translated-audio control
  works after a successful response.
- [ ] Grant/reset permission and record a short Hindi utterance.
- [ ] Stop the recording, select **Translate recording**, and verify the
  `POST /api/speech-translate` request sends `hi-to-en`.
- [ ] Verify progress, Hindi transcript, English
  translation, and playable English audio.
- [ ] Replace a successful audio result with a new recording/result and verify
  playback stops and the previous audio resource is released.
- [ ] Simulate an unsupported or failed audio response and verify a useful
  playback error is displayed.
- [ ] Deny microphone permission and verify clear recovery guidance.
- [ ] Reset while audio is active and verify playback stops and visible state
  clears.
- [ ] Retry after a recoverable failure and verify stale results are not
  retained.

## Error and accessibility checks

- [ ] STT, translation, and TTS failures show separate, recoverable messages
  in test configuration.
- [ ] Errors do not expose Python tracebacks or private local paths.
- [ ] All controls have visible labels and keyboard focus is usable.
- [ ] Loading, success, and error states are visually distinguishable.
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
