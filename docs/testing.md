# Testing

## Default automated suite

From the repository root, activate the project virtual environment and run:

```powershell
python -m pytest
```

For just the end-to-end speech API cases:

```powershell
python -m pytest backend/tests/test_speech_translation_api.py
```

The default suite uses fake providers and FastAPI's in-process test client. It
does not download model weights, require a GPU, or need a running API server.
In particular, `backend/tests/test_speech_translation_api.py` exercises both
English → Hindi and Hindi → English by submitting WAV audio through the
multipart endpoint and checking that the fake STT receives those exact bytes,
the transcript is passed into translation, translated text reaches TTS, and
the response contains the generated audio with encoded text metadata.

## Optional real-model smoke test

Actual local inference is opt-in and separate from the default test suite. It
may download large model weights on first use and requires the optional
dependencies and Windows runtime described in
[the real-model speech smoke test](model-smoke-test.md). Do not run that guide
unless the model downloads and storage location have been approved.
