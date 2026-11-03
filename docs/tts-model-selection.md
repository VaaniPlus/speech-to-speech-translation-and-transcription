# Windows English and Hindi TTS model selection

## Selected implementation

Use the Apache-2.0 licensed **Kokoro-82M** model for the first local English and
Hindi TTS smoke test. Kokoro exposes separate pipeline language codes and voices:

| Application language | Kokoro language code | Selected voice | Quality evidence |
|---|---|---|---|
| English (`en`) | `a` (American English) | `af_heart` | Listed as A overall grade in the official voice catalog |
| Hindi (`hi`) | `h` | `hf_alpha` | Listed as C overall grade; medium target quality and only a few minutes of training audio |

Official sources:

- Model repository: <https://huggingface.co/hexgrad/Kokoro-82M>
- Official project repository: <https://github.com/hexgrad/kokoro>
- Official Python package: <https://pypi.org/project/kokoro/>
- English/Hindi voice catalog: <https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md>
- Kokoro license metadata identifies Apache License 2.0. Review the model card and
  license before release even though the Apache license is generally suitable for
  repository use.

## Windows installation

Use Python 3.11, a virtual environment, and the existing optional model
dependencies. Kokoro itself is installed without adding it to the default test
dependencies:

```powershell
python -m pip install torch torchvision torchaudio
python -m pip install "kokoro>=0.9.4,<1" "soundfile>=0.13,<1"
```

Install `espeak-ng` on Windows using the official Windows MSI installer before
running the real provider. Kokoro/Misaki uses `espeak-ng` for grapheme-to-phoneme
fallback and documents it for Windows.

Official runtime setup:

- eSpeak NG releases: <https://github.com/espeak-ng/espeak-ng/releases>
- Kokoro installation page: <https://pypi.org/project/kokoro/>

Windows should use CPU mode for the first verified path. Kokoro is PyTorch-based,
but this repository does not assume an NVIDIA-compatible execution configuration
until CUDA inference is explicitly smoke-tested. CUDA remains optional in a
future provider; CPU is the portable fallback.

Keep model cache files and generated audio outside the repository. Normal unit
and API tests must continue to use fake providers and must pass without
installing Kokoro or downloading weights.

## Actual local smoke test

The evaluation was recorded on 2026-10-29 in a Windows 11 development environment
using Python 3.11.9, Kokoro 0.9.4, CPU inference, and local cached model files.
The target wording was:

| Language | Input | Output file |
|---|---|---|
| English | `Hello, welcome to the local speech translation system.` | 24 kHz WAV, 3.725 seconds |
| Hindi | `नमस्ते, स्थानीय भाषण अनुवाद प्रणाली में आपका स्वागत है।` | 24 kHz WAV, 5.675 seconds |

The English pipeline required approximately 76 seconds on the first run because it
also downloaded the Kokoro model and the English spaCy tokenizer. The cached
Hindi pipeline initialized in approximately 2.3 seconds on its first measured run.
Warm smoke-run averages were unstable in this Windows process, so individual
results should be treated as observations, not a portable benchmark:

| Run | Average Kokoro pipeline/load time | Average synthesis time | Process RSS |
|---|---:|---:|---:|
| English, 3 warm runs | 7.787 seconds | 7.786 seconds | up to 1239.4 MiB |
| Hindi, 3 warm runs | 4.945 seconds | 15.694 seconds | up to 1241.7 MiB |

For the first uncached English run, synthesis produced a 3.725-second WAV and the
process reached about 1107 MiB RSS. The Hindi run reached about 1214 MiB RSS.
These are RSS observations for Kokoro plus PyTorch and should not be reported as
an exact VRAM measurement; CUDA mode was not exercised.

## Voice-quality observations

Both English and Hindi synthesis completed successfully and produced valid WAV
audio. The English `af_heart` sample is the better-quality reference because the
official catalog grades it as A, while Hindi `hf_alpha` is graded C and Kokoro
lists only a few minutes of Hindi training audio. Hindi quality may include
pronunciation or phoneme-quality artifacts and should receive a manual listening
review before being accepted by users. The generated files are local evaluation
artifacts; they must not be committed to Git.

## Alternatives and exclusions

Piper has an explicit Windows wheel and two useful English/Hindi ONNX voices, but
its current maintained package is GPL-3.0-or-later and individual voice datasets
may have different terms. It remains a viable fallback if legal review accepts
those terms, but Kokoro is selected here because its official model card and
weights identify Apache-2.0 licensing.

Meta MMS-TTS is excluded because its English and Hindi checkpoints are licensed
CC-BY-NC 4.0. Coqui XTTS-v2 supports both languages, but its public model
license requires legal review and does not provide an unambiguously permissive
repository license. Apple MLX-Audio is excluded because it targets Apple MLX and
is not a Windows/NVIDIA solution.

## Decision boundaries

AMTT-21 verified the option and recorded the benchmark protocol. AMTT-22
implements `KokoroTTSProvider` behind `TTSProvider`: English uses pipeline
language `a` and voice `af_heart`, Hindi uses `h` and `hf_alpha`, and output is
mono 24 kHz PCM WAV. Model pipelines load lazily on the first synthesis request
and are reused per language; normal tests inject a fake pipeline and do not
download weights. The adapter defaults to CPU; CUDA requires separate Windows
smoke-test evidence before it is enabled.
