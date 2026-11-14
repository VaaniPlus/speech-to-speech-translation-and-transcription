"""Structural checks for the text-only translation demo set."""

import json
from pathlib import Path


DATASET_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "evaluation"
    / "translation_transcription_demo.json"
)


def test_translation_demo_dataset_has_both_directions_and_required_coverage() -> None:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    cases = dataset["cases"]

    assert dataset["review_status"] == "reviewed_by_competent_bilingual_speaker"
    assert len(cases) == 8
    assert len({case["id"] for case in cases}) == len(cases)
    for case in cases:
        assert case["direction"] in {"en-to-hi", "hi-to-en"}
        assert case["source_text"]
        assert case["expected_transcript"] == case["source_text"]
        assert case["expected_translation"]
        assert set(case) == {
            "id",
            "direction",
            "length",
            "tags",
            "source_text",
            "expected_transcript",
            "expected_translation",
        }

    for direction in {"en-to-hi", "hi-to-en"}:
        direction_cases = [case for case in cases if case["direction"] == direction]
        assert {case["length"] for case in direction_cases} == {"short", "long"}
        assert {
            tag for case in direction_cases for tag in case["tags"]
        } >= {"punctuation", "numbers", "common_name"}
