# API

The FastAPI server provides interactive documentation at `/docs` and an
OpenAPI schema at `/openapi.json`.

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
it in the selected direction. A translation provider must be configured
when the application is created; the API does not silently return fake
or identity translations when no provider is available.

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

### Successful translation response

The response includes the direction, source and target language codes
(`en` or `hi`), source text, translated text, and a `success` status.
`detected_language` is optional because typed-text requests may not use
speech recognition. The source and target language fields must match the
selected direction.

```json
{
  "direction": "en-to-hi",
  "source_text": "Hello",
  "source_language": "en",
  "target_language": "hi",
  "detected_language": null,
  "translated_text": "नमस्ते",
  "status": "success"
}
```

### Errors

Empty/whitespace-only text and unsupported directions return HTTP 422
with FastAPI field-validation details. If no translation provider is
configured, the endpoint returns HTTP 503. A configured provider failure
returns HTTP 502. A missing provider returns HTTP 503 instead of a fake
translation. These provider errors use the stable `ErrorResponse` shape
with a safe message and the `translation` stage.

```json
{
  "status": "error",
  "code": "translation_failed",
  "message": "Translation could not be completed.",
  "stage": "translation"
}
```

```json
{
  "status": "error",
  "code": "translation_provider_unavailable",
  "message": "Translation is not available because no provider is configured.",
  "stage": "translation"
}
```

## Speech-to-text

`POST /api/speech-to-text` accepts `multipart/form-data` with a required
`file` part and an optional `language` field (`en` or `hi`). Omit `language`
for automatic language detection. The endpoint transcribes English or Hindi
audio and returns the transcript, requested and detected language codes,
optional provider confidence, and a success status.

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/speech-to-text `
  -F "file=@speech.wav;type=audio/wav" `
  -F "language=en"
```

Successful response (`200 OK`):

```json
{
  "transcript": "Hello there.",
  "requested_language": "en",
  "detected_language": "en",
  "confidence": 0.94,
  "status": "success"
}
```

The configured maximum upload size is enforced. Empty or malformed audio
returns HTTP 422, unsupported media returns HTTP 415, and oversized audio
returns HTTP 413. These errors use the stable `ErrorResponse` shape with the
`validation` stage. A missing STT provider returns HTTP 503; STT failures return
HTTP 502 with the `stt` stage and a client-safe message. Client filenames are
not used as filesystem paths.
