# Windows English ↔ Hindi translation model selection

## Status and provider choice

The default real text translation provider is **MarianMT** from Helsinki-NLP.
It restores the previously working English ↔ Hindi translation path without
requiring gated model access. Set `TRANSLATION_PROVIDER=indictrans2` to choose
AI4Bharat IndicTrans2 explicitly; that provider uses separate directional
checkpoints:

| Direction | Source/target language codes | Official Hugging Face checkpoint |
|---|---|---|
| English → Hindi (`en-to-hi`) | `eng_Latn` → `hin_Deva` | `ai4bharat/indictrans2-en-indic-dist-200M` |
| Hindi → English (`hi-to-en`) | `hin_Deva` → `eng_Latn` | `ai4bharat/indictrans2-indic-en-dist-200M` |

These are the distilled models listed in the official IndicTrans2 model
documentation. IndicTrans2 is directional: do not rely on a single reverse
checkpoint for both directions. The project will continue to expose stable
application codes `en-to-hi` and `hi-to-en`; the checkpoint codes are mapping
metadata and must not replace them.

The default MarianMT provider uses `Helsinki-NLP/opus-mt-en-hi` and
`Helsinki-NLP/opus-mt-hi-en`, loading only the selected direction. It does not
use `trust_remote_code`.

## Source and license

- Official repository: <https://github.com/AI4Bharat/IndicTrans2>
- Official Hugging Face interface and English/Indic checkpoints:
  <https://github.com/AI4Bharat/IndicTrans2/tree/main/huggingface_interface>
- English → Hindi model:
  <https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M>
- Hindi → English model:
  <https://huggingface.co/ai4bharat/indictrans2-indic-en-dist-200M>
- Model card/license metadata for both checkpoints identifies the MIT license;
  the repository-level license is MIT. Review the final release's model-card and
  repository terms before distribution; license metadata is not substituted
  for legal review.

## Windows installation

Use Python 3.11 and install the optional real-model dependencies from the
repository root:

```powershell
uv sync --project backend --extra ml
```

The `ml` extra pins Transformers below version 5 and includes
`IndicTransToolkit` with its Windows-compatible Indic NLP dependency. It
installs packages, not model weights.

The AI4Bharat checkpoints may require Hugging Face access approval. Request
access on the relevant model page, then authenticate locally with `hf auth
login`; never put the token in source code or share it in chat. English → Hindi
and Hindi → English use separate checkpoints and may require access to each.

For a CUDA-enabled NVIDIA installation, install a PyTorch build that matches
the installed Windows NVIDIA driver/CUDA stack, using the version selector from
PyTorch's official installation page. The implementation may run on CPU if
CUDA is unavailable. Flash Attention is Linux/oriented and should remain
optional; do not enable `attn_implementation="flash_attention_2"` in the
Windows smoke test. `trust_remote_code=True` requires the Hugging Face model
code and must only be used with trusted official AI4Bharat checkpoints.

## Recommended adapter behavior

1. Select the checkpoint from `en-to-hi` or `hi-to-en`.
2. Use the official `IndicProcessor` for pre/post-processing.
3. Use the checkpoint's exact source/target codes (`eng_Latn`, `hin_Deva`).
4. Lazy-load only the selected direction's model/provider.
5. Prefer FP16 on a verified CUDA device and `int8` or FP32 CPU behavior based on
   the installed runtime and measured compatibility. Do not claim a quantization
   configuration works until it is smoke-tested.
6. Run blocking inference in a worker thread or process and raise a controlled
   translation provider error on load/inference failure.
7. Keep model downloads and cache paths outside the repository and outside
   normal mock-provider tests.

## Windows and memory observations

The target machine is a Windows 11 environment with 16 GB RAM and an NVIDIA
RTX 3050-class 6 GB or 4 GB laptop GPU (use the team's exact observed hardware
for final notes). IndicTrans2 is available in both PyTorch CPU and CUDA paths.
CPU is the compatible fallback; it avoids CUDA compatibility risks and does not
require a GPU. Flash Attention should not be assumed compatible with Windows.

The checkpoints are approximately 200–228 million parameters according to
Hugging Face metadata. They therefore require roughly hundreds of megabytes for
weights, with additional tokenizer/runtime/KV-generation memory. The following
is an estimate, not a benchmark:

- GPU inference: target one model at a time; FP16 generally leaves less memory
  overhead than FP32, but CUDA compatibility and final VRAM must be measured.
- CPU inference: 16 GB RAM should be sufficient for a lazy-loaded one-direction
  model with normal application overhead; keep batch size to one for short text.
- Two-direction operation: loading both models simultaneously is unnecessary.
  Prefer lazy loading or unload/replace the active directional model.

VRAM/RAM and latency values are not benchmarked here. A real smoke test must
record actual values on the team Windows environment rather than infer them
from parameter count.

## Manual smoke-test protocol

A member with an approved model environment should run the official adapter and
record the actual source text, output, device, run time, peak RAM/VRAM, and any
failure. Suggested short checks:

| Direction | Input | Targeted manual output |
|---|---|---|
| English → Hindi | `Hello, how are you?` | Hindi equivalent containing natural greeting text, such as `नमस्ते, आप कैसे हैं?` |
| Hindi → English | `नमस्ते, आप कैसे हैं?` | `Hello, how are you?` |

These outputs are examples for manual review, not claims of verified model
output. Both examples are deliberately short so a smoke run can isolate model
loading from long-context behavior. Do not mark manual verification complete until
an actual local run is recorded against both official directional checkpoints.

## Compatibility decision

IndicTrans2 Distilled 200M is the preferred implementation because official
Hugging Face checkpoints support English and Hindi and provide separate
English→Indic and Indic→English directions. Direct `attn_implementation` and
Flash Attention assumptions are incompatible/optional on Windows and are excluded.
Normal Transformers/PyTorch CPU inference is the portable fallback. If either
checkpoint fails loading on the actual Windows/PyTorch stack, record the exact
failure and use the already-isolated mock provider; do not block provider or
API work on the real model. For a replacement, choose another locally runnable
English↔Hindi model only after checking its official source, license, Windows
compatibility, language codes, and memory.

## Documentation boundary

This item documents selection and setup only. A later provider-adapter item owns
code behind `TranslationProvider`; service and route items own application
integration. Normal tests stay fake-provider-only and do not download model
weights.
