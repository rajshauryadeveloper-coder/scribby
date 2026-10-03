import json
from pathlib import Path

from scribby.workers.base import (
    format_transcription_result,
    format_to_srt,
    save_transcription_output,
)


def test_format_transcription_result_structure():
    raw_pipeline_output = {
        "text": " Hello world this is a test.",
        "chunks": [
            {"text": " Hello world", "timestamp": (0.0, 1.5)},
            {"text": " this is a test.", "timestamp": (1.5, 3.2)},
        ],
    }

    result = format_transcription_result(
        audio_path="sample.mp3",
        model_name="openai/whisper-base",
        raw_output=raw_pipeline_output,
        duration_seconds=3.2,
    )

    assert result["audio_filename"] == "sample.mp3"
    assert result["audio_file"].endswith("sample.mp3")
    assert result["model"] == "openai/whisper-base"
    assert "transcribed_at" in result
    assert result["duration"] == 3.2
    assert result["text"] == "Hello world this is a test."
    assert len(result["segments"]) == 2

    seg0 = result["segments"][0]
    assert seg0["id"] == 0
    assert seg0["start"] == 0.0
    assert seg0["end"] == 1.5
    assert seg0["text"] == "Hello world"

    seg1 = result["segments"][1]
    assert seg1["id"] == 1
    assert seg1["start"] == 1.5
    assert seg1["end"] == 3.2
    assert seg1["text"] == "this is a test."


def test_format_to_srt():
    segments = [
        {"id": 0, "start": 1.25, "end": 3.5, "text": "Hello world"},
        {"id": 1, "start": 4.0, "end": 6.8, "text": "Second line"},
    ]
    srt_text = format_to_srt(segments)

    assert "1\n00:00:01,250 --> 00:00:03,500\nHello world" in srt_text
    assert "2\n00:00:04,000 --> 00:00:06,800\nSecond line" in srt_text


def test_save_transcription_output(tmp_path):
    output_data = {
        "audio_file": "speech.wav",
        "model": "openai/whisper-base",
        "transcribed_at": "2026-10-04T00:00:00+05:30",
        "duration": 5.0,
        "text": "Testing output persistence",
        "segments": [
            {"id": 0, "start": 0.0, "end": 5.0, "text": "Testing output persistence"}
        ],
    }

    output_file = save_transcription_output(
        result_data=output_data,
        audio_path="speech.wav",
        output_dir=tmp_path,
        model_name="openai/whisper-base",
    )

    assert output_file.exists()
    assert output_file.suffix == ".json"

    loaded = json.loads(output_file.read_text(encoding="utf-8"))
    assert loaded["model"] == "openai/whisper-base"
    assert loaded["text"] == "Testing output persistence"
    assert len(loaded["segments"]) == 1
