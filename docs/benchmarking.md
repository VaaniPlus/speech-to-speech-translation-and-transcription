# Local speech-pipeline benchmark

[`scripts/benchmark_pipeline.py`](../scripts/benchmark_pipeline.py) measures
the real STT → translation → TTS providers on five short WAV examples
per direction. It reports first-call and subsequent warm-call latency for each
stage, process peak RSS, available CPU/GPU details, configured model IDs, device,
and run settings. This is a small local demo, not a scientific benchmark or a
performance guarantee.

## Prepare audio examples

Provide ten locally stored, consented recordings outside the repository:

```text
<audio-root>\
  en-to-hi\
    01.wav
    02.wav
    03.wav
    04.wav
    05.wav
  hi-to-en\
    01.wav
    02.wav
    03.wav
    04.wav
    05.wav
```

Use short, non-sensitive utterances (maximum 15 seconds per WAV). The script
validates WAV signatures, duration, and the configured upload-size limit. It
selects the first five WAV files in each direction by filename. It does not
store audio or transcripts in the report, and it does not print file names.
Do not commit recordings or reports containing private material.

## Run

Activate the project virtual environment, configure real providers, and keep
the model cache outside the repository. With model downloads disabled (the
default), the script puts Hugging Face libraries into offline mode and requires
the selected model files to already be cached:

```powershell
$env:PROVIDER_MODE = "real"
$env:DEVICE = "cpu"
$env:STT_COMPUTE_TYPE = "int8"
$env:MODEL_CACHE_DIR = "$env:LOCALAPPDATA\VaaniPlus\models"
python .\scripts\benchmark_pipeline.py `
  --audio-root "$env:LOCALAPPDATA\VaaniPlus\benchmark-audio" `
  --output "$env:LOCALAPPDATA\VaaniPlus\amtt-35-report.json"
```

The output path must not already exist; choose a new report filename for each
run so earlier measurements are not overwritten.

Only when downloads have been approved, add `--allow-model-downloads`. The
first call to each lazily loaded model is reported separately; that time
includes both model initialization and inference, so it is not an isolated
load-only measurement. Warm calls default to one additional invocation per
example and stage; adjust with `--warm-repeats`.

The JSON report omits model-cache paths, audio contents, transcripts, and
filenames. It reports the requested device, the configured model IDs, CPU and
system RAM details, and CUDA details when PyTorch can query them. Process peak
RSS is reported where the OS exposes it. PyTorch CUDA peak-allocation numbers do
not include memory allocated by other runtimes, such as CTranslate2; the report
lists this and other limitations explicitly. Compare only runs with the same
models, cache state, hardware, provider configuration, and sample set.

The normal test suite exercises the harness using fake providers and generated
WAV fixtures; it never loads models or downloads weights.
