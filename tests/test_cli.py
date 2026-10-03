import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from scribby.workers.whisper_base_worker import main as base_main
from scribby.workers.whisper_medium_worker import main as medium_main


def test_base_worker_cli_success(tmp_path, monkeypatch):
    audio_file = tmp_path / "cli_test.wav"
    audio_file.write_bytes(b"dummy audio")
    out_dir = tmp_path / "cli_out"

    monkeypatch.setattr(
        sys,
        "argv",
        ["whisper_base_worker.py", str(audio_file), "--output-dir", str(out_dir)],
    )

    mock_pipeline = MagicMock()
    mock_pipeline.return_value = {
        "text": "CLI base test",
        "chunks": [{"text": "CLI base test", "timestamp": (0.0, 1.0)}],
    }

    with patch("scribby.workers.base.ensure_model_available"):
        with patch("scribby.workers.base.pipeline", return_value=mock_pipeline):
            exit_code = base_main()
            assert exit_code == 0
            assert out_dir.exists()
            assert len(list(out_dir.glob("*.json"))) == 1


def test_medium_worker_cli_success(tmp_path, monkeypatch):
    audio_file = tmp_path / "cli_test.wav"
    audio_file.write_bytes(b"dummy audio")
    out_dir = tmp_path / "cli_out"

    monkeypatch.setattr(
        sys,
        "argv",
        ["whisper_medium_worker.py", str(audio_file), "--output-dir", str(out_dir)],
    )

    mock_pipeline = MagicMock()
    mock_pipeline.return_value = {
        "text": "CLI medium test",
        "chunks": [{"text": "CLI medium test", "timestamp": (0.0, 2.0)}],
    }

    with patch("scribby.workers.base.ensure_model_available"):
        with patch("scribby.workers.base.pipeline", return_value=mock_pipeline):
            exit_code = medium_main()
            assert exit_code == 0
            assert out_dir.exists()
            assert len(list(out_dir.glob("*.json"))) == 1


def test_worker_cli_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["whisper_base_worker.py", str(tmp_path / "does_not_exist.wav")],
    )
    exit_code = base_main()
    assert exit_code != 0
