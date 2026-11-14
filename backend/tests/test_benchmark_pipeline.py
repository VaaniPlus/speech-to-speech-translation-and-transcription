"""Offline tests for the benchmark harness; no real models are loaded."""

from pathlib import Path
import wave

import pytest

from app.providers.stt import AudioInput, STTResult
from app.providers.translation import TranslationResult
from app.providers.tts import TTSResult
from scripts.benchmark_pipeline import (
    AudioExample,
    BenchmarkError,
    discover_audio_examples,
    run_benchmark,
)


def write_wav(path: Path, duration_seconds: float = 0.1) -> None:
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16_000)
        wav.writeframes(b"\x00\x00" * int(16_000 * duration_seconds))


def make_audio_examples(root: Path) -> dict[str, list[AudioExample]]:
    examples: dict[str, list[AudioExample]] = {}
    for direction in ("en-to-hi", "hi-to-en"):
        directory = root / direction
        directory.mkdir(parents=True)
        paths = []
        for index in range(5):
            path = directory / f"private-name-{index:02d}.wav"
            write_wav(path)
            paths.append(
                AudioExample(f"{direction}-{index + 1:02d}", direction, path)
            )
        examples[direction] = paths
    return examples


def test_audio_discovery_requires_five_per_direction_and_hides_filenames(
    tmp_path: Path,
) -> None:
    for direction in ("en-to-hi", "hi-to-en"):
        directory = tmp_path / direction
        directory.mkdir()
        for index in range(6):
            write_wav(directory / f"private-name-{index:02d}.wav")

    examples = discover_audio_examples(tmp_path)

    assert [example.sample_id for example in examples["en-to-hi"]] == [
        f"en-to-hi-{index:02d}" for index in range(1, 6)
    ]
    assert all(len(direction_examples) == 5 for direction_examples in examples.values())
    assert all(
        "private-name" not in example.sample_id
        for direction_examples in examples.values()
        for example in direction_examples
    )

    (tmp_path / "hi-to-en" / "private-name-04.wav").unlink()
    (tmp_path / "hi-to-en" / "private-name-05.wav").unlink()
    with pytest.raises(BenchmarkError, match="at least 5 WAV files"):
        discover_audio_examples(tmp_path)


def test_run_benchmark_records_cold_and_warm_stage_calls_without_payloads(
    tmp_path: Path,
) -> None:
    class FakeSTT:
        def transcribe(self, audio: AudioInput, language: str) -> STTResult:
            assert audio.data.startswith(b"RIFF")
            return STTResult("test transcript", language=language)

    class FakeTranslation:
        def translate(self, source_text: str, direction: str) -> TranslationResult:
            assert source_text == "test transcript"
            return TranslationResult(f"translated {direction}")

    class FakeTTS:
        def synthesize(self, text: str, target_language: str) -> TTSResult:
            assert text.startswith("translated")
            assert target_language in {"en", "hi"}
            return TTSResult(b"test audio")

    examples = make_audio_examples(tmp_path)
    report = run_benchmark(
        examples,
        FakeSTT(),
        FakeTranslation(),
        FakeTTS(),
        max_audio_size_bytes=1024 * 1024,
        warm_repeats=1,
    )

    assert report["examples_measured"] == {"en-to-hi": 5, "hi-to-en": 5}
    assert report["stage_latency_ms"]["stt"]["shared"]["warm_calls_ms"]["count"] == 19
    assert set(report["stage_latency_ms"]["translation"]) == {"en-to-hi", "hi-to-en"}
    assert set(report["stage_latency_ms"]["tts"]) == {"en", "hi"}
    assert all(
        group["cold_first_call_ms"] >= 0
        for stage in report["stage_latency_ms"].values()
        for group in stage.values()
    )
    serialized = repr(report)
    assert "private-name" not in serialized
    assert "test transcript" not in serialized


def test_run_benchmark_rejects_long_wav_before_provider_calls(tmp_path: Path) -> None:
    examples = make_audio_examples(tmp_path)
    example = examples["en-to-hi"][0]
    write_wav(example.path, duration_seconds=16)

    with pytest.raises(BenchmarkError, match="Audio duration exceeds"):
        run_benchmark(
            examples,
            object(),
            object(),
            object(),
            max_audio_size_bytes=1024 * 1024,
            warm_repeats=1,
        )
