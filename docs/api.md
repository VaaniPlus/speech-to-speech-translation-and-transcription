# API

The FastAPI server provides interactive documentation at `/docs` and an
OpenAPI schema at `/openapi.json`.

The documented application routes are `GET /api/health`,
`POST /api/translate`, `POST /api/speech-to-text`, and
`POST /api/speech-translate`. This server is intended for local development.

## Development browser access

The API allows browser requests only from `http://localhost:5500` and
`http://127.0.0.1:5500`, without credentialed CORS. Serve the frontend from
one of these origins; opaque `Origin: null` requests (including direct
`file://` pages) are not allowed. The allowed request headers are
`Content-Type`; exposed response headers include the speech metadata headers,
`Content-Disposition`, and `X-Request-ID`.

## Health

`GET /api/health` reports whether the API process is running. It does not load
or download speech models.

Successful response (`200 OK`):

```json
{
  "status": "ok"
}
```

Run the API tests from the repository root with `python -m pytest`. These tests
use FastAPI's in-process test client and do not require model downloads or a
GPU.

## Typed-text translation

`POST /api/translate` accepts typed English or Hindi text and translates
it in the selected direction. In the default `PROVIDER_MODE=mock`, the
application installs deterministic fake providers; their output is not real
translation. In `PROVIDER_MODE=real`, the configured local model providers are
used. If a provider is explicitly unavailable, the endpoint returns a safe
503 error rather than an identity translation.

Each synchronous model-provider call is limited by
`PROVIDER_TIMEOUT_SECONDS` (default: 120 seconds). A timed-out provider returns
HTTP 504 with a stable error code and stage.

### Translation request

The request accepts only `en-to-hi` or `hi-to-en`. The `source_text`
field must contain non-whitespace text; surrounding whitespace is
removed during validation.

```json
{
  "direction": "en-to-hi",
  "source_text": "Hello"
}
```

### Translation response example

The response includes the direction, source and target language codes
(`en` or `hi`), source text, translated text, and a `success` status.
`detected_language` is `null` for this typed-text example. The example below
shows the default fake provider's literal output, not a Hindi translation;
real-provider wording varies by model.

```json
{
  "direction": "en-to-hi",
  "source_text": "Hello",
  "source_language": "en",
  "target_language": "hi",
  "detected_language": null,
  "translated_text": "[mock en-to-hi] Hello",
  "status": "success"
}
```

### Errors

Empty/whitespace-only text and unsupported directions return HTTP 422
with the stable `ErrorResponse` shape. If no translation provider is
configured, the endpoint returns HTTP 503. A configured provider failure
returns HTTP 502. These provider errors use the stable `ErrorResponse` shape
with a safe message and the `translation` stage.

```json
{
  "status": "error",
  "code": "translation_failed",
  "message": "Translation could not be completed.",
  "stage": "translation",
  "request_id": "0123456789abcdef0123456789abcdef"
}
```

```json
{
  "status": "error",
  "code": "translation_provider_unavailable",
  "message": "Translation is not available because no provider is configured.",
  "stage": "translation",
  "request_id": "0123456789abcdef0123456789abcdef"
}
```

Timeouts use HTTP 504; for example:

```json
{
  "status": "error",
  "code": "translation_timeout",
  "message": "Translation timed out.",
  "stage": "translation",
  "request_id": "0123456789abcdef0123456789abcdef"
}
```

Every response emitted by an API endpoint includes the same correlation ID in
the `X-Request-ID` header.
Provider errors and timeouts are logged with that ID, stage, stable error code,
and exception type; provider exception messages and local paths are not
returned.

## Speech-to-text

`POST /api/speech-to-text` accepts `multipart/form-data` with a required
`file` part and an optional `language` field (`en` or `hi`). Omit `language`
for automatic language detection. The endpoint transcribes English or Hindi
audio and returns the transcript, requested and detected language codes,
optional provider confidence, and a success status.

Supported media types are `audio/wav`, `audio/mpeg`, `audio/flac`, `audio/ogg`,
`audio/webm`, and `audio/mp4`. Accepted aliases are `audio/x-wav`,
`audio/wave`, `audio/mp3`, `audio/x-m4a`, and `application/ogg`; they are
normalized to the corresponding media type. The declared media type is checked
against the file signature. Both speech endpoints enforce the configurable
`MAX_UPLOAD_SIZE_BYTES` limit, which defaults to 25 MiB.

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/speech-to-text `
  -F "file=@speech.wav;type=audio/wav" `
  -F "language=en"
```

Successful response (`200 OK`):

```json
{
  "transcript": "[mock transcription]",
  "requested_language": "en",
  "detected_language": "en",
  "confidence": 1.0,
  "status": "success"
}
```

This response is the default fake STT output, not an actual transcription.
Empty input returns HTTP 422 (`empty_audio`). A WAV file with a valid WAV
signature but invalid or truncated WAV data returns HTTP 422 (`invalid_audio`);
a signature that does not match the declared media type returns HTTP 415
(`unsupported_audio_type`). Oversized audio returns HTTP 413
(`audio_too_large`). Errors use the stable `ErrorResponse` shape with the
`validation` stage. An unsupported language hint returns HTTP 422
(`unsupported_language`). A missing STT provider returns HTTP 503; STT failures
return HTTP 502 and timeouts return HTTP 504 with the `stt` stage and a
client-safe message. Client filenames are ignored and are never interpreted
as filesystem paths.

## Speech-to-speech translation

`POST /api/speech-translate` accepts `multipart/form-data` with a required
`file` part and a required `direction` field (`en-to-hi` or `hi-to-en`).
Direction determines the source-language hint passed to STT and the language
used by TTS. The request runs transcription, translation, and synthesis in
order.

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/speech-translate `
  -F "file=@speech.wav;type=audio/wav" `
  -F "direction=en-to-hi" `
  -o translated-speech.wav `
  -D speech-translation-headers.txt
```

### Successful response

The response body is only the generated audio file, with its provider-selected
audio content type and a `Content-Disposition` filename. Text metadata is
returned in HTTP headers; the transcript and translated text header values are
percent-encoded UTF-8 so non-ASCII Hindi text remains safe in HTTP headers.
Clients should URL-decode those two values as UTF-8.

| Header | Value |
|---|---|
| `X-Transcript` | Percent-encoded source transcript |
| `X-Translated-Text` | Percent-encoded translation |
| `X-Source-Language` | `en` or `hi` |
| `X-Target-Language` | `hi` or `en` |
| `X-Translation-Direction` | `en-to-hi` or `hi-to-en` |
| `X-Request-ID` | Request correlation ID |
| `Content-Disposition` | Attachment filename for the generated audio |

This is a file response, not a JSON/binary multipart body. Browsers can create
a playable object URL from the response body and read the metadata headers.
`Access-Control-Expose-Headers` includes the metadata and file headers and
`X-Request-ID` for correlation.

Invalid direction or audio returns HTTP 4xx with the `validation` stage. A
source-language mismatch returns HTTP 422 with stage `stt`. Provider failures
return HTTP 502, and unavailable providers return HTTP 503; both use the stable
`ErrorResponse` shape and identify the failed stage (`stt`, `translation`, or
`tts`) without returning provider details or tracebacks. Provider timeouts
return HTTP 504 with a stage-specific code. All API errors use the stable
`ErrorResponse` schema and include their `X-Request-ID` correlation header.

With the default fake providers, speech processing returns a placeholder
transcript and translation plus the bytes `MOCK_AUDIO_NOT_REAL_SPEECH`, which
are not playable speech. Use real local providers to evaluate speech output;
do not treat mock output as a language-quality result.

## Data handling and limitations

The browser keeps a recording in memory and sends it to the local API only
after the user selects **Translate recording**. Uploads are size/type checked;
temporary STT files are removed after inference, including failure paths. The
application does not log raw audio or full transcript/translation text by
default. No endpoint accepts arbitrary filesystem paths. Real inference runs
through local providers, but the first use may
download model packages or weights from their configured hosting sources.

The product supports only English and Hindi. Recognition, translation, and
synthesis quality depends on the selected models, audio, and hardware; the
demo set and performance script are not scientific benchmarks and make no
quality or latency guarantee. For browser controls, privacy behavior, and
known user-facing limitations, see the [frontend user guide](../frontend/README.md).
