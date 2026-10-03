import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from scribby.workers.base import ensure_model_available, get_default_model_dir


def test_get_default_model_dir():
    base_dir = get_default_model_dir("openai/whisper-base")
    medium_dir = get_default_model_dir("openai/whisper-medium")

    assert base_dir.name == "whisper-base"
    assert medium_dir.name == "whisper-medium"
    assert "models" in str(base_dir)


def test_ensure_model_available_already_exists(tmp_path):
    model_dir = tmp_path / "whisper-base"
    model_dir.mkdir(parents=True)
    # Simulate existing downloaded model files
    (model_dir / "config.json").write_text("{\"model_type\": \"whisper\"}")
    (model_dir / "model.safetensors").write_text("dummy weights")

    with patch("scribby.workers.base.snapshot_download") as mock_download:
        resolved_path = ensure_model_available("openai/whisper-base", local_dir=model_dir)
        assert resolved_path == model_dir
        mock_download.assert_not_called()


def test_ensure_model_available_downloads_when_missing(tmp_path):
    model_dir = tmp_path / "whisper-base"

    with patch("scribby.workers.base.snapshot_download") as mock_download:
        resolved_path = ensure_model_available("openai/whisper-base", local_dir=model_dir)
        assert resolved_path == model_dir
        mock_download.assert_called_once_with(
            repo_id="openai/whisper-base",
            local_dir=str(model_dir),
        )


def test_ensure_model_available_downloads_when_empty_dir(tmp_path):
    model_dir = tmp_path / "whisper-base"
    model_dir.mkdir(parents=True)  # empty directory

    with patch("scribby.workers.base.snapshot_download") as mock_download:
        resolved_path = ensure_model_available("openai/whisper-base", local_dir=model_dir)
        assert resolved_path == model_dir
        mock_download.assert_called_once()
