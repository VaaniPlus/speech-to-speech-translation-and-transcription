# Requirements and acceptance tests

## 1. Purpose and scope

The project is a local-first browser application for speech translation
between English and Hindi. A user may provide microphone audio or typed
text, then receives the source transcript (or typed source), translated
text, and generated target-language audio.

Supported directions:

- `en-to-hi`: English source to Hindi translation.
- `hi-to-en`: Hindi source to English translation.

## 2. Functional requirements

| ID | Requirement |
|---|---|
| FR-01 | The UI shall allow the user to select only `en-to-hi` or `hi-to-en`. |
| FR-02 | The UI shall start microphone capture only after an explicit user action and permission grant. |
| FR-03 | The UI shall provide start, stop, reset/cancel, and submit controls. |
| FR-04 | The backend shall accept microphone audio and identify or validate the selected source language. |
| FR-05 | The backend shall transcribe the spoken source language and return the source transcript. |
| FR-06 | The backend shall translate source text in the selected direction. |
| FR-07 | The backend shall generate target-language speech and return playable audio. |
| FR-08 | The UI shall show source text/transcript and translated text separately. |
| FR-09 | The UI shall offer typed-text fallback that uses the same translation pipeline. |
| FR-10 | The UI shall expose loading, success, cancellation, permission-denied, and recoverable error states. |
| FR-11 | Invalid input shall return a useful client error; provider failures shall return a safe server error. |
| FR-12 | API documentation and setup instructions shall be available locally. |

## 3. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-01 | The development target shall be Python 3.11 on Windows. |
| NFR-02 | The application shall run locally without sending data to external services by default. |
| NFR-03 | STT, translation, and TTS model code shall be replaceable provider boundaries. |
| NFR-04 | Automated tests shall use deterministic fake providers and shall not download models or require a GPU. |
| NFR-05 | Long-running model calls shall not block the API event loop. |
| NFR-06 | Logs shall not include raw audio or full private transcript text by default. |
| NFR-07 | Request and response schemas shall be typed and consistent. |
| NFR-08 | Secrets, model weights, recordings, generated audio, caches, and virtual environments shall not be committed. |
| NFR-09 | The UI shall remain usable on a desktop browser and be keyboard accessible. |
| NFR-10 | Temporary audio files shall be cleaned up after success or failure. |

## 4. User journeys

### 4.1 English to Hindi speech

1. The user opens the application and selects `en-to-hi`.
2. The user starts recording and grants microphone permission.
3. The UI records audio and displays recording/progress state.
4. The user stops recording and submits the captured audio.
5. The backend validates and transcribes the English audio.
6. The backend translates the transcript into Hindi and synthesizes Hindi
   speech.
7. The UI displays the English transcript and Hindi translation.
8. The user plays, pauses, or replay the generated audio.
9. The user may reset the result and start again.

Expected acceptance result: valid English speech produces a separate
English transcript, a Hindi translation, and browser-playable Hindi audio.

### 4.2 Hindi to English speech

1. The user opens the application and selects `hi-to-en`.
2. The user starts recording and grants microphone permission.
3. The UI records Hindi audio and displays recording/progress state.
4. The user stops recording and submits the captured audio.
5. The backend validates and transcribes the Hindi audio.
6. The backend translates the transcript into English and synthesizes
   English speech.
7. The UI displays the Hindi transcript and English translation.
8. The user plays, pauses, or replay the generated audio.
9. The user may reset the result and start again.

Expected acceptance result: valid Hindi speech produces a separate Hindi
transcript, an English translation, and browser-playable English audio.

### 4.3 Typed-text fallback

1. The user selects a translation direction.
2. The user enters non-empty text in the source language.
3. The user submits the text without microphone access.
4. The backend validates and translates the text.
5. The UI displays source text and translated text.
6. Empty or whitespace-only input produces a useful validation message.

## 5. Error and recovery acceptance cases

- Recording without permission must explain microphone access and must
  not crash or leave media tracks running.
- Unsupported or empty audio must produce a clear client error.
- STT, translation, or TTS failure must identify the affected stage
  without exposing a traceback or private local path.
- A failed request must permit retry or reset.
- Rapid duplicate submissions must not overwrite a newer result.
- A reset must stop playback and clear visible results and errors.
- Loading, success, and error states must be visibly distinguishable.

## 6. Out of scope

The following are explicitly excluded from this release:

- languages other than English and Hindi;
- translation plus transliteration as a combined feature;
- live full-duplex or multi-party conversations;
- meeting, call, or continuous-session recording;
- cloud-hosted accounts, profile data, or cloud storage;
- cloud-hosted inference or deployment;
- voice cloning or speaker identity preservation;
- advanced scientific translation-quality benchmarking; and
- mobile-specific UI or native applications.

## 7. Acceptance test matrix

| Scenario | Required evidence |
|---|---|
| English → Hindi typed text | API response contains source text, `en-to-hi`, Hindi text, and success status. |
| Hindi → English typed text | API response contains source text, `hi-to-en`, English text, and success status. |
| Invalid direction or empty text | API returns a useful 4xx response and UI does not display stale output. |
| English → Hindi speech | Source English transcript, Hindi translation, and audio are returned and play successfully. |
| Hindi → English speech | Source Hindi transcript, English translation, and audio are returned and play successfully. |
| Provider failure | The UI shows a recoverable stage-specific error; no internal stack trace is exposed. |
| Microphone denied | The UI explains permission recovery and releases no active capture resources. |
| Automated test suite | Tests use fakes and pass without model downloads or GPU access. |
| Keyboard and layout | Primary controls are visible, labeled, keyboard reachable, and usable on desktop. |

## 8. Instructor-facing demo criteria

The demo must be repeatable without model downloads or external network
calls. The presenter shall demonstrate:

1. A clear project scope and the two supported directions.
2. Typed English → Hindi translation and typed Hindi → English translation.
3. English speech → Hindi transcript/translation/audio where local models
   are available.
4. Hindi speech → English transcript/translation/audio where local models
   are available.
5. A microphone-denied or invalid-input recovery case.
6. Separation of source transcript and translated text.
7. Provider-independent automated tests using fake adapters.
8. Repository setup, test command, API documentation, and known
   limitations.

A demo may use documented fake providers when real local models are not
available, but must distinguish mock output from real model quality. Final
acceptance is not a claim of perfect translation quality; it requires both
directions to be demonstrated, controlled errors to be visible, and setup
and tests to be repeatable by another team member.
