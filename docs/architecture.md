# Architecture

## System context

The application is a local-first English ↔ Hindi speech translation system.
The browser owns microphone access and UI state. The FastAPI backend validates
requests and orchestrates provider boundaries. STT, translation, and TTS
implementations run behind replaceable interfaces and may execute locally.

```text
┌──────────────────────────────────────┐
│ Browser                              │
│                                      │
│ Direction selector                   │
│ Microphone capture / typed text      │
│ Source transcript + translated text  │
│ Generated audio player               │
└──────────────────┬───────────────────┘
                   │ HTTP JSON / multipart upload
                   ▼
┌──────────────────────────────────────┐
│ FastAPI application                  │
│                                      │
│ Routes → validation → service layer  │
│                  ├─ STT provider     │
│                  ├─ Translation      │
│                  └─ TTS provider     │
│                                      │
│ Stable schemas + controlled errors   │
└──────────────────┬───────────────────┘
                   │ provider calls
                   ▼
┌──────────────────────────────────────┐
│ Local model runtime                  │
│                                      │
│ STT: English/Hindi transcription     │
│ Translation: English ↔ Hindi         │
│ TTS: target-language speech synthesis│
└──────────────────────────────────────┘
```

## Components

### Browser UI

The UI owns explicit microphone permission, media capture, direction selection,
submission state, transcript display, and playback lifecycle. It sends only:

- JSON text requests for typed translation; or
- multipart audio requests for speech processing.

The browser must not import or configure model implementations.

### API routes

Route handlers are thin adapters for HTTP concerns. They:

1. validate request shape and supported directions;
2. select the configured service/provider implementations through dependency
   injection or application configuration;
3. map controlled service errors to documented HTTP responses; and
4. serialize stable Pydantic response schemas or audio responses.

Route handlers never call model libraries, download weights, or access model
configuration directly.

### Service layer

The service layer coordinates application behavior independently of FastAPI
request objects. It maps the requested direction to source and target languages,
orchestrates required stages, records stage timings in structured logs, and
converts provider failures into controlled domain errors.

A text translation service is not responsible for audio capture. A speech
orchestration service may call STT, translation, and TTS in sequence, but
provider interfaces remain independently replaceable.

### Provider boundaries

#### Speech-to-text

`STTProvider` accepts `AudioInput` or raw bytes and returns a typed `STTResult`
with transcript, detected or requested language metadata, confidence, and optional
metadata. It is responsible only for transcription. Invalid audio, empty input,
unsupported language, and inference failures are represented as provider exceptions.
The shared upload utility checks allowlisted `audio/wav`, `audio/mpeg`,
`audio/flac`, `audio/ogg`, `audio/webm`, and `audio/mp4` MIME types against file
signatures, enforces `MAX_UPLOAD_SIZE_BYTES` with bounded reads when passed the
configured limit, and checks WAV duration when a duration limit is configured.
Other accepted formats do not get duration checks without a decoder. Temporary
STT files use generated names and MIME-derived extensions; client filenames are
ignored and files are removed after inference.

In `PROVIDER_MODE=real`, the application uses the lazy
`FasterWhisperSTTProvider`; it loads optional ML dependencies and model weights
when inference begins. Development and default automated tests use
`FakeSTTProvider`, which has no network or model-download side effects. The
selected Windows candidate and isolated loading requirements are recorded in
[STT model selection](stt-model-selection.md).

#### Translation

`TranslationProvider` accepts source text and a supported direction. It returns
plain translated text or a typed `TranslationResult` containing source/target
language metadata. Direction-to-language mapping is centralized in configuration
or a small policy type rather than in route handlers.

In `PROVIDER_MODE=real`, the application uses
`IndicTrans2TranslationProvider` with separate English-to-Hindi and
Hindi-to-English checkpoints. Development and tests use
`FakeTranslationProvider`, which returns visibly prefixed mock output and must
not be described as real translation. The provider boundary prevents route and
service code from depending on a model package or model identifier.
`PROVIDER_MODE=mock` also installs fake STT and TTS providers with no network or
model-download side effects. The configured IndicTrans2 checkpoints, official
sources, language codes, Windows setup, and verification notes are recorded in
[translation model selection](translation-model-selection.md).

#### Text-to-speech

`TTSProvider` accepts target text and a target language, then returns raw bytes,
a typed `TTSResult` with format/content metadata, or a `ManagedAudioArtifact`.
Empty text, unsupported language, and synthesis failures are represented explicitly.

In `PROVIDER_MODE=real`, the application uses `KokoroTTSProvider` with the
configured English and Hindi model IDs. The current adapter runs on CPU.
Development and tests use `FakeTTSProvider`; its placeholder bytes are not
playable speech and must not be presented as synthesized speech or quality
evidence. The selected voices, Windows requirements, and quality limitations
are recorded in [TTS model selection](tts-model-selection.md).

## Request and response flow

### Typed-text translation

```text
Browser
  → POST /api/translate (direction, text)
  → route validation
  → translation service
  → translation provider
  → stable JSON response
  ← source text, translated text, direction, status
  ↳ stage timings recorded in logs
```

### Speech translation

```text
Browser
  → explicit microphone action
  → optional local media encoding
  → POST /api/speech-translate (multipart audio, direction)
  → route validation / audio utilities
  → orchestration service
  → STT provider → transcript
  → Translation provider → target text
  → TTS provider → generated audio
  → audio-file response body with percent-encoded text metadata headers
  ← transcript, translated text, language/direction headers, and playable audio
```

The response body contains only generated audio; source transcript, translated
text, language codes, and direction are returned in documented HTTP headers.
The text headers are percent-encoded UTF-8. A mixed JSON/binary body is not
used. Client filenames are never interpreted as paths.

## Error handling

Provider and application errors are classified before they reach HTTP handlers:

- validation error: clear 4xx response describing the field or unsupported
  value;
- unavailable provider or stage timeout: controlled 5xx response with a stable
  error code and stage (`stt`, `translation`, or `tts`);
- invalid or unsupported media: clear 4xx response; and
- unexpected failure: safe 5xx response with a request correlation ID, while
  the server logs operational details.

All JSON errors use the stable `ErrorResponse` schema, including a request ID
that also appears in the `X-Request-ID` response header. The configured
`PROVIDER_TIMEOUT_SECONDS` deadline applies to each synchronous model-provider
call. A timed-out wait returns a stage-specific HTTP 504 response; the
underlying Python worker thread cannot be forcibly stopped and may finish in
the background. Timeout and provider error logs include the request ID, stage,
stable error code, and exception type.

Route responses must not expose Python tracebacks, model package exceptions,
or machine-specific paths. Raw audio and full transcript text are not logged by
default.

Application logs are newline-delimited JSON written to standard error (the
local Uvicorn terminal by default). Request events include the request ID,
HTTP outcome, and duration; each STT, translation, and TTS stage records its
own outcome and duration. Provider failures record exception type and stable
error code without logging exception messages or input/output payloads. To
retain logs locally, redirect standard error to a file such as
`.\vaani-api.log`; `*.log` files are ignored by Git.

## Asynchronous execution and local resources

Provider inference must not execute blocking model calls directly on the FastAPI
event loop. Synchronous provider calls run through the shared worker-thread
helper with a per-call timeout. `create_app` constructs provider objects from
validated settings; model weights remain lazy and are not downloaded merely by
starting the API. The current application lifespan logs startup and shutdown;
it does not load or unload model weights. Model caches and generated audio must
remain outside Git.

## Security and privacy boundaries

- microphone capture requires explicit browser action and permission;
- the default mock runtime sends no audio or text to external services; real
  providers run locally, while first-use model downloads contact their
  configured hosting sources;
- upload size/type limits and temporary-file cleanup are enforced;
- CORS allows only `http://localhost:5500` and `http://127.0.0.1:5500` in
  development; opaque `Origin: null` and other origins are not allowed;
- arbitrary client filenames and filesystem paths are never accepted or reused;
- secrets and environment-specific values stay outside Git; and
- operational logs contain stage timing and outcomes rather than raw payloads.

## Architectural constraints

- English and Hindi are the only supported languages in this version.
- No route handler imports or invokes a concrete STT, translation, or TTS
  implementation.
- Provider interfaces return typed values and controlled domain exceptions.
- Services remain independent of FastAPI request/response objects.
- Automated tests use fake providers and do not download model weights.
- Real-model smoke tests are optional, local, and separate from the default
  test suite.
