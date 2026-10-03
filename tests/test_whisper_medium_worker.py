from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from scribby.workers.whisper_medium_worker import WhisperMediumWorker, transcribe_audio


def test_whisper_medium_worker_init():
    worker = WhisperMediumWorker()
    assert worker.model_id == "openai/whisper-medium"
    assert worker.model_slug == "whisper-medium"


def test_whisper_medium_worker_file_not_found(tmp_path):
    worker = WhisperMediumWorker()
    with pytest.raises(FileNotFoundError):
        worker.transcribe(tmp_path / "non_existent.wav")


def test_whisper_medium_worker_transcribe_mocked(tmp_path):
    audio_file = tmp_path / "interview.mp3"
    audio_file.write_bytes(b"dummy audio data")

    output_dir = tmp_path / "outputs"

    mock_pipeline = MagicMock()
    mock_pipeline.return_value = {
        "text": "Hello Whisper Medium",
        "chunks": [
            {"text": "Hello Whisper Medium", "timestamp": (0.0, 3.5)}
        ],
    }

    with patch("scribby.workers.base.ensure_model_available") as mock_ensure:
        mock_ensure.return_value = tmp_path / "model_dir"
        with patch("scribby.workers.base.pipeline", return_value=mock_pipeline):
            worker = WhisperMediumWorker(output_dir=output_dir)
            result = worker.transcribe(audio_file)

            assert result["model"] == "openai/whisper-medium"
            assert result["text"] == "Hello Whisper Medium"
            assert len(result["segments"]) == 1
            assert result["segments"][0]["start"] == 0.0
            assert result["segments"][0]["end"] == 3.5

            # Verify saved file
            assert "output_file" in result
            saved_path = Path(result["output_file"])
            assert saved_path.exists()
            assert saved_path.suffix == ".json"


def test_whisper_medium_worker_helper_function(tmp_path):
    audio_file = tmp_path / "podcast.mp3"
    audio_file.write_bytes(b"dummy audio data")

    mock_pipeline = MagicMock()
    mock_pipeline.return_value = {
        "text": "Medium helper test",
        "chunks": [{"text": "Medium helper test", "timestamp": (0.0, 2.5)}],
    }

    with patch("scribby.workers.base.ensure_model_available"):
        with patch("scribby.workers.base.pipeline", return_value=mock_pipeline):
            result = transcribe_audio(audio_file, output_dir=tmp_path / "outs")
            assert result["text"] == "Medium helper test"
            assert result["model"] == "openai/whisper-medium"
