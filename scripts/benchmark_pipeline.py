"""Opt-in local benchmark for the real English/Hindi speech pipeline."""

from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import statistics
import sys
import time
from typing import Any, Callable, Literal

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.config import Settings, load_settings
from app.providers.faster_whisper_stt import FasterWhisperSTTProvider
from app.providers.indictrans2_translation import IndicTrans2TranslationProvider
from app.providers.kokoro_tts import KokoroTTSProvider
from app.providers.stt import (
    AudioInput,
    STTProvider,
    STTProviderError,
    STTResult,
)
from app.providers.translation import (
    TranslationProvider,
    TranslationProviderError,
    TranslationResult,
)
from app.providers.tts import (
    ManagedAudioArtifact,
    TTSProvider,
    TTSProviderError,
    TTSResult,
)
from app.utils.audio import AudioInputError, validate_audio_data

Direction = Literal["en-to-hi", "hi-to-en"]
DIRECTIONS: tuple[Direction, ...] = ("en-to-hi", "hi-to-en")
LANGUAGES_BY_DIRECTION: dict[Direction, tuple[str, str]] = {
    "en-to-hi": ("en", "hi"),
    "hi-to-en": ("hi", "en"),
}
EXAMPLES_PER_DIRECTION = 5
MAX_AUDIO_DURATION_SECONDS = 15
PROVIDER_ERRORS = (STTProviderError, TranslationProviderError, TTSProviderError)


@dataclass(frozen=True)
class AudioExample:
    sample_id: str
    direction: Direction
    path: Path


class BenchmarkError(Exception):
    """A clear input or output problem that prevents a valid benchmark."""


class BenchmarkStageError(BenchmarkError):
    """A provider failure annotated with the stage being measured."""

    def __init__(self, stage: str, error: Exception) -> None:
        self.stage = stage
        self.error_type = type(error).__name__
        super().__init__(f"{stage} failed ({self.error_type}): {error}")


def discover_audio_examples(audio_root: Path) -> dict[Direction, list[AudioExample]]:
    """Select five short WAV samples per direction without exposing filenames."""
    examples: dict[Direction, list[AudioExample]] = {}
    for direction in DIRECTIONS:
        directory = audio_root / direction
        if not directory.is_dir():
            raise BenchmarkError(f"Missing audio directory for {direction}.")

        paths = sorted(
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix.lower() == ".wav"
        )
        if len(paths) < EXAMPLES_PER_DIRECTION:
            raise BenchmarkError(
                f"{direction} requires at least {EXAMPLES_PER_DIRECTION} WAV files."
            )
        examples[direction] = [
            AudioExample(
                sample_id=f"{direction}-{index:02d}",
                direction=direction,
                path=path,
            )
            for index, path in enumerate(paths[:EXAMPLES_PER_DIRECTION], start=1)
        ]
    return examples


def load_audio_example(example: AudioExample, max_size_bytes: int) -> AudioInput:
    """Read and validate one short WAV without retaining its filename."""
    try:
        data = example.path.read_bytes()
    except OSError as error:
        raise BenchmarkError(
            f"Could not read {example.direction} sample {example.sample_id}."
        ) from error
    try:
        return validate_audio_data(
            data,
            "audio/wav",
            max_size_bytes=max_size_bytes,
            max_duration_seconds=MAX_AUDIO_DURATION_SECONDS,
        )
    except AudioInputError as error:
        raise BenchmarkError(
            f"Invalid {example.direction} sample {example.sample_id}: {error}"
        ) from error


def summarize_latencies(values: list[float]) -> dict[str, float | int]:
    if not values:
        raise ValueError("At least one latency value is required.")
    return {
        "count": len(values),
        "min": round(min(values), 3),
        "median": round(statistics.median(values), 3),
        "max": round(max(values), 3),
    }


def _translation_text(result: str | TranslationResult) -> str:
    text = result.translated_text if isinstance(result, TranslationResult) else result
    if not isinstance(text, str) or not text.strip():
        raise BenchmarkError("Translation returned no usable text.")
    return text.strip()


def _validate_tts_result(result: object) -> None:
    if isinstance(result, TTSResult):
        if not result.audio_bytes:
            raise BenchmarkError("TTS returned empty audio.")
    elif isinstance(result, ManagedAudioArtifact):
        if not Path(result.uri).is_file():
            raise BenchmarkError("TTS returned a missing audio artifact.")
    elif not isinstance(result, bytes) or not result:
        raise BenchmarkError("TTS returned no usable audio.")


def run_benchmark(
    examples_by_direction: dict[Direction, list[AudioExample]],
    stt_provider: STTProvider,
    translation_provider: TranslationProvider,
    tts_provider: TTSProvider,
    *,
    max_audio_size_bytes: int,
    warm_repeats: int,
    synchronize: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Measure direct provider calls; first calls include lazy model loading."""
    if warm_repeats < 1:
        raise ValueError("warm_repeats must be at least one.")

    cold_calls: set[tuple[str, str]] = set()
    stage_data: dict[str, dict[str, dict[str, Any]]] = {
        "stt": {},
        "translation": {},
        "tts": {},
    }
    observed_devices: dict[str, Any] = {
        "stt": "unreported",
        "translation": {},
        "tts": {},
    }
    per_example: list[dict[str, Any]] = []

    def measure(
        stage: str,
        group: str,
        action: Callable[[], Any],
    ) -> tuple[Any, float, bool]:
        if synchronize is not None:
            synchronize()
        started = time.perf_counter()
        try:
            result = action()
        except PROVIDER_ERRORS as error:
            raise BenchmarkStageError(stage, error) from error
        if synchronize is not None:
            synchronize()
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)

        bucket = stage_data[stage].setdefault(
            group,
            {"cold_first_call_ms": None, "warm_calls_ms": []},
        )
        call_key = (stage, group)
        is_cold = call_key not in cold_calls
        if is_cold:
            bucket["cold_first_call_ms"] = elapsed_ms
            cold_calls.add(call_key)
        else:
            bucket["warm_calls_ms"].append(elapsed_ms)
        return result, elapsed_ms, is_cold

    for direction in DIRECTIONS:
        direction_examples = examples_by_direction.get(direction, [])
        if len(direction_examples) < EXAMPLES_PER_DIRECTION:
            raise BenchmarkError(
                f"{direction} requires at least {EXAMPLES_PER_DIRECTION} examples."
            )
        source_language, target_language = LANGUAGES_BY_DIRECTION[direction]
        for example in direction_examples[:EXAMPLES_PER_DIRECTION]:
            audio = load_audio_example(example, max_audio_size_bytes)
            row: dict[str, Any] = {
                "sample_id": example.sample_id,
                "direction": direction,
                "first_pass_ms": {},
                "warm_calls_ms": {"stt": [], "translation": [], "tts": []},
                "cold_start_stages": [],
            }

            def transcribe() -> STTResult:
                result = stt_provider.transcribe(audio, language=source_language)
                if not isinstance(result, STTResult) or not result.transcript.strip():
                    raise BenchmarkError("STT returned no usable transcript.")
                observed_devices["stt"] = str(
                    result.metadata.get("device", "unreported")
                )
                return result

            transcript, elapsed, is_cold = measure("stt", "shared", transcribe)
            row["first_pass_ms"]["stt"] = elapsed
            if is_cold:
                row["cold_start_stages"].append("stt")

            def translate() -> str:
                result = translation_provider.translate(
                    transcript.transcript,
                    direction,
                )
                if isinstance(result, TranslationResult):
                    observed_devices["translation"][direction] = str(
                        result.metadata.get("device", "unreported")
                    )
                else:
                    observed_devices["translation"][direction] = "unreported"
                return _translation_text(result)

            translated_text, elapsed, is_cold = measure(
                "translation",
                direction,
                translate,
            )
            row["first_pass_ms"]["translation"] = elapsed
            if is_cold:
                row["cold_start_stages"].append("translation")

            def synthesize(text: str) -> None:
                result = tts_provider.synthesize(text, target_language)
                _validate_tts_result(result)
                metadata = result.metadata if isinstance(result, TTSResult) else {}
                observed_devices["tts"][target_language] = str(
                    metadata.get("device", "cpu (provider default)")
                )

            _, elapsed, is_cold = measure(
                "tts",
                target_language,
                lambda: synthesize(translated_text),
            )
            row["first_pass_ms"]["tts"] = elapsed
            if is_cold:
                row["cold_start_stages"].append("tts")

            for _ in range(warm_repeats):
                warm_transcript, elapsed, _ = measure(
                    "stt",
                    "shared",
                    transcribe,
                )
                row["warm_calls_ms"]["stt"].append(elapsed)

                def warm_translate() -> str:
                    result = translation_provider.translate(
                        warm_transcript.transcript,
                        direction,
                    )
                    return _translation_text(result)

                warm_text, elapsed, _ = measure(
                    "translation",
                    direction,
                    warm_translate,
                )
                row["warm_calls_ms"]["translation"].append(elapsed)
                _, elapsed, _ = measure(
                    "tts",
                    target_language,
                    lambda: synthesize(warm_text),
                )
                row["warm_calls_ms"]["tts"].append(elapsed)
            per_example.append(row)

    summarized: dict[str, dict[str, dict[str, Any]]] = {}
    for stage, groups in stage_data.items():
        summarized[stage] = {}
        for group, values in groups.items():
            summarized[stage][group] = {
                "cold_first_call_ms": values["cold_first_call_ms"],
                "warm_calls_ms": summarize_latencies(values["warm_calls_ms"]),
            }

    return {
        "examples_measured": {
            direction: EXAMPLES_PER_DIRECTION for direction in DIRECTIONS
        },
        "observed_devices": observed_devices,
        "stage_latency_ms": summarized,
        "per_example_timings": per_example,
    }


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def system_memory_bytes() -> int | None:
    if os.name == "nt":
        status = _MemoryStatusEx()
        status.dwLength = ctypes.sizeof(status)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(_MemoryStatusEx)]
        kernel32.GlobalMemoryStatusEx.restype = wintypes.BOOL
        if not kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(status.ullTotalPhys)
    if hasattr(os, "sysconf"):
        page_size = os.sysconf("SC_PAGE_SIZE")
        page_count = os.sysconf("SC_PHYS_PAGES")
        return int(page_size * page_count)
    return None


class _ProcessMemoryCounters(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def peak_process_rss_bytes() -> tuple[int | None, str]:
    if os.name == "nt":
        counters = _ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(_ProcessMemoryCounters),
            wintypes.DWORD,
        ]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        if not psapi.GetProcessMemoryInfo(
            kernel32.GetCurrentProcess(),
            ctypes.byref(counters),
            counters.cb,
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(counters.PeakWorkingSetSize), "Windows peak working set"
    status_path = Path("/proc/self/status")
    if status_path.is_file():
        for line in status_path.read_text(encoding="ascii").splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1]) * 1024, "Linux VmHWM peak RSS"
    if sys.platform == "darwin":
        import resource

        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss), "macOS peak RSS"
    return None, "unavailable on this operating system"


def torch_runtime() -> Any | None:
    try:
        import torch
    except ImportError:
        return None
    return torch


def environment_report(torch_module: Any | None) -> dict[str, Any]:
    processor = platform.processor() or platform.uname().processor or "unknown"
    if torch_module is None:
        gpu: dict[str, Any] = {
            "available": None,
            "probe": "PyTorch could not be imported",
        }
    elif torch_module.cuda.is_available():
        properties = torch_module.cuda.get_device_properties(0)
        gpu = {
            "available": True,
            "name": torch_module.cuda.get_device_name(0),
            "total_memory_bytes": int(properties.total_memory),
        }
    else:
        gpu = {"available": False}
    return {
        "os": platform.platform(),
        "python": platform.python_version(),
        "cpu": processor,
        "logical_cpu_count": os.cpu_count(),
        "system_memory_bytes": system_memory_bytes(),
        "gpu": gpu,
    }


def build_report(
    settings: Settings,
    allow_model_downloads: bool,
    warm_repeats: int,
    torch_module: Any | None,
    benchmark_results: dict[str, Any],
) -> dict[str, Any]:
    if torch_module is not None and torch_module.cuda.is_available():
        torch_module.cuda.synchronize()
        gpu_memory: dict[str, Any] = {
            "pytorch_peak_allocated_bytes": int(
                torch_module.cuda.max_memory_allocated()
            ),
            "pytorch_peak_reserved_bytes": int(
                torch_module.cuda.max_memory_reserved()
            ),
        }
    else:
        gpu_memory = {
            "pytorch_peak_allocated_bytes": None,
            "pytorch_peak_reserved_bytes": None,
        }
    process_peak, memory_method = peak_process_rss_bytes()
    return {
        "benchmark": "small local speech-translation demo; not a scientific benchmark",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": environment_report(torch_module),
        "configuration": {
            "provider_mode": settings.provider_mode,
            "requested_device": settings.device,
            "stt_compute_type": settings.stt_compute_type,
            "models": {
                "stt": settings.stt_model_id,
                "translation": {
                    "en-to-hi": settings.translation_en_hi_model_id,
                    "hi-to-en": settings.translation_hi_en_model_id,
                },
                "tts": {
                    "en": settings.tts_en_model_id,
                    "hi": settings.tts_hi_model_id,
                },
            },
            "model_downloads_allowed": allow_model_downloads,
            "model_cache_path_recorded": False,
            "tts_device": "cpu (provider configuration)",
        },
        "method": {
            "examples_per_direction": EXAMPLES_PER_DIRECTION,
            "maximum_wav_duration_seconds": MAX_AUDIO_DURATION_SECONDS,
            "warm_repeats_per_example": warm_repeats,
            "cold_first_call_includes_lazy_model_load_and_inference": True,
            "audio_and_transcript_contents_recorded": False,
        },
        "results": benchmark_results,
        "memory": {
            "process_peak_rss_bytes": process_peak,
            "process_peak_measurement": memory_method,
            **gpu_memory,
        },
        "limitations": [
            "The first call includes lazy model loading and inference; it is not an isolated load-only measurement.",
            "Cold calls use cached weights unless model downloads were explicitly enabled.",
            "PyTorch CUDA memory excludes allocations made by other runtimes such as CTranslate2.",
            "Only the first five WAV files in each direction, sorted by filename, are measured.",
            "Timing and memory results describe this machine and run only; they are not performance guarantees.",
            "The benchmark does not score translation, transcription, or speech quality.",
        ],
    }


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure local real-model speech translation stage latency and memory."
    )
    parser.add_argument(
        "--audio-root",
        required=True,
        type=Path,
        help="Folder containing en-to-hi and hi-to-en subfolders with short WAV files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON report path; without it, the report is printed to stdout.",
    )
    parser.add_argument(
        "--warm-repeats",
        type=int,
        default=1,
        help="Number of additional warm calls per example and stage (default: 1).",
    )
    parser.add_argument(
        "--allow-model-downloads",
        action="store_true",
        help="Allow the providers to download missing model files.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = make_parser()
    args = parser.parse_args(argv)
    if args.warm_repeats < 1:
        parser.error("--warm-repeats must be at least 1.")

    try:
        examples = discover_audio_examples(args.audio_root)
        settings = load_settings()
    except (BenchmarkError, ValueError) as error:
        print(f"Benchmark setup failed: {error}", file=sys.stderr)
        return 2
    if settings.provider_mode != "real":
        print(
            "Benchmark requires PROVIDER_MODE=real; mock timings are not model benchmarks.",
            file=sys.stderr,
        )
        return 2

    if not args.allow_model_downloads:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"

    stt_provider = FasterWhisperSTTProvider(
        model_id=settings.stt_model_id,
        device=settings.device,
        compute_type=settings.stt_compute_type,
        cache_dir=settings.model_cache_dir,
    )
    translation_provider = IndicTrans2TranslationProvider(
        en_hi_model_id=settings.translation_en_hi_model_id,
        hi_en_model_id=settings.translation_hi_en_model_id,
        device=settings.device,
        cache_dir=settings.model_cache_dir,
    )
    tts_provider = KokoroTTSProvider(
        en_model_id=settings.tts_en_model_id,
        hi_model_id=settings.tts_hi_model_id,
    )
    torch_module = torch_runtime()
    cuda_available = torch_module is not None and torch_module.cuda.is_available()
    synchronize = (
        torch_module.cuda.synchronize
        if cuda_available and settings.device in ("auto", "cuda")
        else None
    )
    if synchronize is not None:
        torch_module.cuda.reset_peak_memory_stats()

    try:
        benchmark_results = run_benchmark(
            examples,
            stt_provider,
            translation_provider,
            tts_provider,
            max_audio_size_bytes=settings.max_upload_size_bytes,
            warm_repeats=args.warm_repeats,
            synchronize=synchronize,
        )
        report = build_report(
            settings,
            args.allow_model_downloads,
            args.warm_repeats,
            torch_module,
            benchmark_results,
        )
        serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.output is None:
            print(serialized, end="")
        else:
            with args.output.open("x", encoding="utf-8") as report_file:
                report_file.write(serialized)
            print(f"Benchmark report written to {args.output}")
    except (BenchmarkError, OSError) as error:
        print(f"Benchmark failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
