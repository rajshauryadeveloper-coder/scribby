from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from scribby.workers.whisper_base_worker import WhisperBaseWorker, transcribe_audio


def test_whisper_base_worker_init():
    worker = WhisperBaseWorker()
    assert worker.model_id == "openai/whisper-base"
    assert worker.model_slug == "whisper-base"


def test_whisper_base_worker_file_not_found(tmp_path):
    worker = WhisperBaseWorker()
    with pytest.raises(FileNotFoundError):
        worker.transcribe(tmp_path / "non_existent.wav")


def test_whisper_base_worker_transcribe_mocked(tmp_path):
    audio_file = tmp_path / "sample.wav"
    audio_file.write_bytes(b"dummy audio data")

    output_dir = tmp_path / "outputs"

    mock_pipeline = MagicMock()
    mock_pipeline.return_value = {
        "text": "Hello Whisper Base",
        "chunks": [
            {"text": "Hello Whisper Base", "timestamp": (0.0, 2.0)}
        ],
    }

    with patch("scribby.workers.base.ensure_model_available") as mock_ensure:
        mock_ensure.return_value = tmp_path / "model_dir"
        with patch("scribby.workers.base.pipeline", return_value=mock_pipeline):
            worker = WhisperBaseWorker(output_dir=output_dir)
            result = worker.transcribe(audio_file)

            assert result["model"] == "openai/whisper-base"
            assert result["text"] == "Hello Whisper Base"
            assert len(result["segments"]) == 1
            assert result["segments"][0]["start"] == 0.0
            assert result["segments"][0]["end"] == 2.0

            # Verify saved file
            assert "output_file" in result
            saved_path = Path(result["output_file"])
            assert saved_path.exists()
            assert saved_path.suffix == ".json"


def test_whisper_base_worker_helper_function(tmp_path):
    audio_file = tmp_path / "sample.wav"
    audio_file.write_bytes(b"dummy audio data")

    mock_pipeline = MagicMock()
    mock_pipeline.return_value = {
        "text": "Function helper test",
        "chunks": [{"text": "Function helper test", "timestamp": (0.0, 1.0)}],
    }

    with patch("scribby.workers.base.ensure_model_available"):
        with patch("scribby.workers.base.pipeline", return_value=mock_pipeline):
            result = transcribe_audio(audio_file, output_dir=tmp_path / "outs")
            assert result["text"] == "Function helper test"
            assert result["model"] == "openai/whisper-base"
