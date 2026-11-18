# Windows English ↔ Hindi translation

## Selected provider

The backend uses the Helsinki-NLP MarianMT models for real typed-text and
speech-pipeline translation:

| Direction | Model |
|---|---|
| English → Hindi (`en-to-hi`) | `Helsinki-NLP/opus-mt-en-hi` |
| Hindi → English (`hi-to-en`) | `Helsinki-NLP/opus-mt-hi-en` |

Only the model for the requested direction is loaded. Model files are
downloaded from Hugging Face on first use and cached locally. MarianMT uses the
standard Transformers model API and does not require `trust_remote_code` or a
Hugging Face access token.

## Setup

Install the project's optional local inference dependencies from the repository
root:

```powershell
uv sync --project backend --extra ml
```

Set `PROVIDER_MODE=real` in `backend/.env` to enable local model providers.
The [Windows setup guide](windows-setup.md) describes the environment options,
external model cache, and troubleshooting steps.

## Runtime notes

- The first request for a direction downloads and initializes that model; later
  requests reuse it.
- CPU inference is supported. Translation uses the configured local
  Transformers/PyTorch environment.
- Mock mode is for workflow testing only and returns placeholder text, not a
  real translation.
- Model output quality and latency depend on the input and hardware. A short
  smoke test is not a quality benchmark.

## Manual smoke test

After enabling real providers and starting the backend, submit these examples
in both directions and check that the result is in the target language:

| Direction | Input |
|---|---|
| English → Hindi | `Hello, how are you?` |
| Hindi → English | `नमस्ते, आप कैसे हैं?` |

The exact wording may vary. Record the model/cache state and elapsed time if
measuring performance; do not treat these sample phrases as benchmark data.
