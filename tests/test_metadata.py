"""Unit and integration tests for worker metadata, progress tracking, and streamer."""

import io
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from scribby.workers.metadata import (
    ConsoleProgressReporter,
    ProgressTracker,
    TranscriptionMetadata,
    TranscriptionProgress,
    WhisperMetadataStreamer,
)
from scribby.workers.whisper_base_worker import WhisperBaseWorker, transcribe_audio


# ============================================================================
# 1. Dataclass & Model Tests
# ============================================================================

def test_transcription_progress_to_dict():
    progress = TranscriptionProgress(
        status="transcribing",
        progress_percentage=45.5,
        words_per_second=15.2,
        words_per_minute=912.0,
        elapsed_time_seconds=2.5,
        word_count=38,
        current_text="Hello world this is a test",
        audio_duration=10.0,
        processed_duration=4.5,
        file_path="/path/to/output.json",
        metadata_extra={"custom": "val"},
    )
    d = progress.to_dict()
    assert d["status"] == "transcribing"
    assert d["progress_percentage"] == 45.5
    assert d["words_per_second"] == 15.2
    assert d["words_per_minute"] == 912.0
    assert d["elapsed_time_seconds"] == 2.5
    assert d["word_count"] == 38
    assert d["current_text"] == "Hello world this is a test"
    assert d["audio_duration"] == 10.0
    assert d["processed_duration"] == 4.5
    assert d["file_path"] == "/path/to/output.json"
    assert d["metadata_extra"] == {"custom": "val"}


def test_transcription_metadata_to_dict():
    metadata = TranscriptionMetadata(
        progress_percentage=100.0,
        words_per_second=18.33333,
        words_per_minute=1100.0,
        execution_time_seconds=1.23456,
        file_path="/path/to/file.json",
        output_srt_path="/path/to/file.srt",
        word_count=25,
        audio_duration=5.0,
        real_time_factor=4.05,
    )
    d = metadata.to_dict()
    assert d["progress_percentage"] == 100.0
    assert d["words_per_second"] == 18.33
    assert d["words_per_minute"] == 1100.0
    assert d["execution_time_seconds"] == 1.235
    assert d["file_path"] == "/path/to/file.json"
    assert d["output_srt_path"] == "/path/to/file.srt"
    assert d["word_count"] == 25
    assert d["audio_duration"] == 5.0
    assert d["real_time_factor"] == 4.05


# ============================================================================
# 2. ProgressTracker Unit Tests
# ============================================================================

def test_progress_tracker_lifecycle():
    events = []

    def callback(snap: TranscriptionProgress):
        events.append(snap)

    tracker = ProgressTracker(audio_duration=10.0, callback=callback)
    assert tracker.status == "pending"

    # Start
    tracker.start()
    assert tracker.status == "starting"
    assert len(events) == 1
    assert events[0].status == "starting"
    assert events[0].progress_percentage == 0.0

    # Simulate chunk update
    tracker.update(
        current_text="Hello world",
        processed_duration=5.0,
    )
    assert len(events) == 2
    assert events[1].status == "transcribing"
    assert events[1].word_count == 2
    assert events[1].progress_percentage == 50.0
    assert events[1].words_per_second >= 0.0
    assert events[1].words_per_minute >= 0.0

    # Complete
    meta = tracker.complete(
        output_file="test_out.json",
        output_srt_path="test_out.srt",
        final_text="Hello world complete transcription",
    )
    assert len(events) == 3
    assert events[2].status == "completed"
    assert events[2].progress_percentage == 100.0
    assert events[2].word_count == 4
    assert meta.word_count == 4
    assert meta.progress_percentage == 100.0
    assert meta.file_path is not None
    assert meta.output_srt_path is not None
    assert meta.execution_time_seconds >= 0.0


def test_progress_tracker_callback_error_resilience():
    def broken_callback(snap):
        raise RuntimeError("Callback crashed!")

    tracker = ProgressTracker(audio_duration=5.0, callback=broken_callback)
    # Should not raise exception
    tracker.start()
    tracker.update(current_text="Safe test")
    meta = tracker.complete(final_text="Safe test")
    assert meta.word_count == 2


def test_progress_tracker_fail():
    events = []
    tracker = ProgressTracker(audio_duration=5.0, callback=lambda s: events.append(s))
    tracker.start()
    tracker.fail("Pipeline decode error")

    assert tracker.status == "failed"
    assert len(events) == 2
    assert events[1].status == "failed"
    assert events[1].metadata_extra.get("error") == "Pipeline decode error"


def test_progress_tracker_post_complete_updates_ignored():
    tracker = ProgressTracker(audio_duration=5.0)
    tracker.start()
    tracker.complete(final_text="Done")
    # Subsequent update should be ignored
    tracker.update(current_text="Ignored text")
    assert tracker.word_count == 1
    assert tracker.status == "completed"


# ============================================================================
# 3. WhisperMetadataStreamer Unit Tests
# ============================================================================

def test_whisper_metadata_streamer():
    mock_tokenizer = MagicMock()

    # Simulate token mapping:
    # 50364 -> <|0.00|>
    # 50464 -> <|2.00|>
    # 101 -> "Hello"
    # 102 -> " World"
    def mock_convert_ids_to_tokens(tid):
        mapping = {
            50364: "<|0.00|>",
            50464: "<|2.00|>",
            101: "Hello",
            102: " World",
        }
        return mapping.get(tid, "")

    def mock_decode(tokens, skip_special_tokens=True):
        res = []
        for t in tokens:
            if t == 101:
                res.append("Hello")
            elif t == 102:
                res.append(" World")
        return "".join(res)

    mock_tokenizer.convert_ids_to_tokens.side_effect = mock_convert_ids_to_tokens
    mock_tokenizer.decode.side_effect = mock_decode

    events = []
    tracker = ProgressTracker(audio_duration=4.0, callback=lambda s: events.append(s))
    tracker.start()

    streamer = WhisperMetadataStreamer(
        tokenizer=mock_tokenizer,
        tracker=tracker,
        chunk_length_s=30.0,
    )

    # Feed start timestamp token and text token
    streamer.put([50364, 101])
    assert tracker.current_text == "Hello"
    assert tracker.word_count == 1

    # Feed second text token and end timestamp token
    streamer.put([102, 50464])
    assert tracker.current_text == "Hello World"
    assert tracker.word_count == 2
    assert tracker.processed_duration == 2.0
    assert tracker.progress_percentage == 50.0  # 2.0 / 4.0 * 100

    streamer.end()
    assert streamer.base_audio_offset == 2.0


# ============================================================================
# 4. ConsoleProgressReporter Unit Tests
# ============================================================================

def test_console_progress_reporter(monkeypatch):
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)

    reporter = ConsoleProgressReporter(quiet=False, is_tty=True)
    snap = TranscriptionProgress(
        status="transcribing",
        progress_percentage=75.0,
        words_per_second=20.0,
        words_per_minute=1200.0,
        elapsed_time_seconds=3.5,
        word_count=70,
    )
    reporter(snap)

    output_str = out.getvalue()
    assert "75.0%" in output_str
    assert "20.0 words/s" in output_str
    assert "1200.0 wpm" in output_str

    # Test completed status clears line
    completed_snap = TranscriptionProgress(
        status="completed",
        progress_percentage=100.0,
        words_per_second=20.0,
        words_per_minute=1200.0,
        elapsed_time_seconds=4.0,
        word_count=80,
    )
    reporter(completed_snap)


def test_console_progress_reporter_quiet(monkeypatch):
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)

    reporter = ConsoleProgressReporter(quiet=True)
    snap = TranscriptionProgress(
        status="transcribing",
        progress_percentage=50.0,
        words_per_second=10.0,
        words_per_minute=600.0,
        elapsed_time_seconds=2.0,
        word_count=20,
    )
    reporter(snap)
    assert out.getvalue() == ""


# ============================================================================
# 5. Worker Metadata Integration Tests
# ============================================================================

def test_worker_transcribe_includes_complete_metadata(tmp_path):
    audio_file = tmp_path / "meta_test.wav"
    audio_file.write_bytes(b"dummy audio")
    out_dir = tmp_path / "outs"

    mock_pipeline = MagicMock()
    mock_pipeline.tokenizer = None  # Test non-streamer fallback path
    mock_pipeline.return_value = {
        "text": "Metadata verification test audio content.",
        "chunks": [{"text": "Metadata verification test audio content.", "timestamp": (0.0, 3.0)}],
    }

    events = []

    def on_progress(p: TranscriptionProgress):
        events.append(p)

    with patch("scribby.workers.base.ensure_model_available"):
        with patch("scribby.workers.base.pipeline", return_value=mock_pipeline):
            worker = WhisperBaseWorker(output_dir=out_dir)
            result = worker.transcribe(
                audio_file,
                save_output=True,
                generate_srt=True,
                progress_callback=on_progress,
            )

            # Metadata assertions on result dict
            assert "metadata" in result
            meta = result["metadata"]
            assert meta["progress_percentage"] == 100.0
            assert meta["word_count"] == 5
            assert meta["execution_time_seconds"] >= 0.0
            assert meta["words_per_second"] >= 0.0
            assert meta["words_per_minute"] >= 0.0
            assert meta["file_path"] is not None
            assert meta["output_srt_path"] is not None
            assert Path(meta["file_path"]).exists()
            assert Path(meta["output_srt_path"]).exists()

            # Verify saved JSON contains the metadata block
            saved_json = json.loads(Path(meta["file_path"]).read_text(encoding="utf-8"))
            assert "metadata" in saved_json
            assert saved_json["metadata"]["progress_percentage"] == 100.0
            assert saved_json["metadata"]["file_path"] == meta["file_path"]
            assert saved_json["metadata"]["output_srt_path"] == meta["output_srt_path"]
            assert saved_json["metadata"]["word_count"] == 5

            # Verify progress events were received
            assert len(events) >= 2
            assert events[0].status == "starting"
            assert events[-1].status == "completed"
            assert events[-1].progress_percentage == 100.0


def test_helper_transcribe_audio_progress_callback(tmp_path):
    audio_file = tmp_path / "helper_test.wav"
    audio_file.write_bytes(b"dummy audio")

    mock_pipeline = MagicMock()
    mock_pipeline.tokenizer = None
    mock_pipeline.return_value = {
        "text": "Helper function test",
        "chunks": [{"text": "Helper function test", "timestamp": (0.0, 1.0)}],
    }

    progress_called = False

    def on_progress(p: TranscriptionProgress):
        nonlocal progress_called
        progress_called = True

    with patch("scribby.workers.base.ensure_model_available"):
        with patch("scribby.workers.base.pipeline", return_value=mock_pipeline):
            result = transcribe_audio(
                audio_file,
                output_dir=tmp_path / "outs",
                progress_callback=on_progress,
            )
            assert progress_called is True
            assert "metadata" in result
            assert result["metadata"]["progress_percentage"] == 100.0
            assert result["metadata"]["word_count"] == 3
