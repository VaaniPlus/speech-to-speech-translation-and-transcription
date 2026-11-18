# Windows STT model selection

## Selected model

Use **`Systran/faster-whisper-small`** for the first local smoke test. Its
runtime is [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper), which
uses CTranslate2. It is a multilingual model and can transcribe English and
Hindi; it is also small enough to start with on CPU or a laptop GPU.

The Hugging Face conversion repository describes the model as `openai/whisper-small`
converted to FP16 CTranslate2 format. The repository and package metadata identify
`faster-whisper` as MIT licensed. The underlying Whisper weights are Apache 2.0
licensed. Confirm licenses and acceptable-use terms for the deployed release and
organization before distribution.

## Official setup

For this Python 3.11 project, install the optional model dependency only in an
environment that will run a real STT provider:

```powershell
uv sync --project backend --extra ml
```

The default test setup does not install this dependency, does not load a model,
and does not download model weights. This keeps mock-provider tests and normal
API startup offline.

The package should be upgraded only together with its CTranslate2/CUDA
compatibility. GPU mode requires NVIDIA cuBLAS and cuDNN 9 for CUDA 12 in current
`ctranslate2` releases. CPU mode should use `int8` first for lower memory use,
for example by selecting `compute_type="int8"` in a future provider adapter.

## CPU/GPU mode

| Mode | Configuration | Observation |
|---|---|---|
| CPU | `device="cpu"`, quantized `int8` preferred | Suitable fallback when CUDA libraries or a compatible GPU are unavailable. |
| GPU | `device="cuda"`, FP16 or tested quantization | Use only after cuBLAS/cuDNN compatibility is installed and CUDA execution is verified. |

These modes should be selected by provider configuration, never by a route or
import-time model load. A missing CUDA installation or unavailable provider must
return a controlled provider error; it must not make mock mode dependent on ML
packages.

## This environment

Recorded on 2026-10-29 from the local development environment:

- OS: Microsoft Windows 11, Windows NT 10.0 build 26300
- CPU: 12th Gen Intel Core i7-12650H
- System RAM: 15.6 GB
- GPU: NVIDIA GeForce RTX 3050 A Laptop GPU
- GPU memory: 4094 MiB

This is a development observation, not a model-smoke benchmark. No model package
was installed and no model was downloaded during this evaluation. CPU or GPU
latency, RAM, and VRAM should be measured with a short English/Hindi audio sample
when AMTT-15 implements the adapter.

## Boundaries and acceptance

- Loading `faster-whisper` is optional and belongs only in a concrete STT provider.
- Mock STT remains [development/test-only fake provider code](../backend/app/providers/fake.py),
  with no real-model claim.
- Test suites use the provider protocol with fake implementations and must pass
  without downloading weights or installing the optional ML dependencies.
- A real provider should expose configuration for device and compute type, isolate
  inference from the async event loop, clean up temporary files, and raise
  `STTProviderError` for controlled failures.
