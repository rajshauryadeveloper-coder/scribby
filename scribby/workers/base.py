"""Base worker and utilities for speech-to-text transcription using Whisper."""

import json
import logging
import os
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import torch
from huggingface_hub import snapshot_download
from transformers import pipeline

# Load environment variables if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("scribby.workers")


def get_repo_root() -> Path:
    """Find the root directory of the repository."""
    # Assuming this file is in scribby/workers/base.py
    current_path = Path(__file__).resolve()
    for parent in [current_path.parent.parent.parent, current_path.parent.parent, current_path.parent]:
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent
    return Path.cwd()


def get_default_models_dir() -> Path:
    """Returns the default base directory for storing local model weights."""
    models_dir_env = os.getenv("MODELS_DIR", "models")
    path = Path(models_dir_env)
    if not path.is_absolute():
        path = get_repo_root() / path
    return path


def get_default_outputs_dir(subfolder: Optional[str] = "transcriptions") -> Path:
    """Returns the default directory for saving transcription outputs."""
    outputs_dir_env = os.getenv("OUTPUTS_DIR", "outputs")
    path = Path(outputs_dir_env)
    if not path.is_absolute():
        path = get_repo_root() / path
    if subfolder:
        path = path / subfolder
    return path



def get_default_model_dir(model_id: str, base_dir: Optional[Union[Path, str]] = None) -> Path:
    """Returns the specific directory path for a given model ID."""
    parent = Path(base_dir) if base_dir else get_default_models_dir()
    slug = model_id.split("/")[-1]
    return parent / slug


def get_optimal_device() -> str:
    """Determine the optimal device available for inference."""
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def ensure_model_available(
    model_id: str,
    local_dir: Optional[Union[Path, str]] = None,
) -> Path:
    """
    Ensure the specified Hugging Face model is downloaded and available locally.
    
    If the model files already exist locally, download is skipped.
    Otherwise, downloads the full repository snapshot to the local directory.
    """
    target_dir = Path(local_dir) if local_dir else get_default_model_dir(model_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    # Check if key model configuration files exist
    config_file = target_dir / "config.json"
    has_weights = any(
        target_dir.glob("*.safetensors")
    ) or any(
        target_dir.glob("*.bin")
    ) or any(
        target_dir.glob("model.*")
    )

    if config_file.exists() and has_weights:
        logger.info(f"Model '{model_id}' found locally in '{target_dir}'. Skipping download.")
        return target_dir

    logger.info(f"Downloading model '{model_id}' to local directory '{target_dir}'...")
    try:
        snapshot_download(
            repo_id=model_id,
            local_dir=str(target_dir),
            ignore_patterns=["*.msgpack", "*.h5", "*.ot", "flax_model*", "tf_model*"],
        )
        logger.info(f"Successfully downloaded model '{model_id}' to '{target_dir}'.")
    except Exception as e:
        logger.error(f"Failed to download model '{model_id}' to '{target_dir}': {e}")
        raise

    return target_dir


def get_audio_duration(audio_path: Union[Path, str]) -> Optional[float]:
    """Attempt to calculate audio duration in seconds."""
    path = Path(audio_path)
    if not path.exists():
        return None

    # Try standard wave module first (for .wav files)
    try:
        with wave.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate > 0:
                return round(frames / float(rate), 2)
    except Exception:
        pass

    # Try soundfile if available
    try:
        import soundfile as sf
        info = sf.info(str(path))
        return round(float(info.duration), 2)
    except Exception:
        pass

    return None


def format_seconds_to_srt_time(seconds: float) -> str:
    """Format seconds into SRT timestamp string HH:MM:SS,mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_to_srt(segments: List[Dict[str, Any]]) -> str:
    """Convert segment chunks into standard SubRip (SRT) format text."""
    srt_entries = []
    for idx, seg in enumerate(segments, start=1):
        start_sec = seg.get("start", 0.0) or 0.0
        end_sec = seg.get("end") or (start_sec + 2.0)
        start_str = format_seconds_to_srt_time(start_sec)
        end_str = format_seconds_to_srt_time(end_sec)
        text = seg.get("text", "").strip()
        srt_entries.append(f"{idx}\n{start_str} --> {end_str}\n{text}\n")
    return "\n".join(srt_entries)


def format_transcription_result(
    audio_path: Union[Path, str],
    model_name: str,
    raw_output: Dict[str, Any],
    duration_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Format raw transformers speech recognition output into a clean,
    timestamped, database-ready dictionary.
    """
    audio_path_obj = Path(audio_path)
    full_text = raw_output.get("text", "").strip()
    raw_chunks = raw_output.get("chunks", [])

    segments: List[Dict[str, Any]] = []

    if raw_chunks:
        for idx, chunk in enumerate(raw_chunks):
            ts = chunk.get("timestamp")
            if ts and isinstance(ts, (tuple, list)):
                start = round(float(ts[0]), 3) if ts[0] is not None else 0.0
                end = round(float(ts[1]), 3) if len(ts) > 1 and ts[1] is not None else None
            else:
                start = 0.0
                end = None

            segments.append({
                "id": idx,
                "start": start,
                "end": end,
                "text": chunk.get("text", "").strip(),
            })
    elif full_text:
        # Fallback if no chunks were provided
        segments.append({
            "id": 0,
            "start": 0.0,
            "end": duration_seconds,
            "text": full_text,
        })

    # Estimate duration from segments if not known
    if duration_seconds is None and segments:
        last_end = segments[-1].get("end")
        if last_end is not None:
            duration_seconds = last_end

    now_iso = datetime.now(timezone.utc).astimezone().isoformat()

    return {
        "audio_file": str(audio_path_obj.resolve()),
        "audio_filename": audio_path_obj.name,
        "model": model_name,
        "transcribed_at": now_iso,
        "duration": duration_seconds,
        "text": full_text,
        "segments": segments,
    }


def save_transcription_output(
    result_data: Dict[str, Any],
    audio_path: Union[Path, str],
    output_dir: Optional[Union[Path, str]] = None,
    model_name: Optional[str] = None,
    save_srt: bool = False,
) -> Path:
    """
    Persist transcription results into structured timestamped files in output folder.
    Returns the path to the primary saved JSON file.
    """
    target_dir = Path(output_dir) if output_dir else get_default_outputs_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    audio_stem = Path(audio_path).stem
    model_slug = (model_name or result_data.get("model", "whisper")).split("/")[-1]
    timestamp_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"{audio_stem}_{model_slug}_{timestamp_tag}"

    json_file_path = target_dir / f"{base_filename}.json"
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved transcription JSON to: {json_file_path}")

    if save_srt:
        srt_file_path = target_dir / f"{base_filename}.srt"
        srt_content = format_to_srt(result_data.get("segments", []))
        with open(srt_file_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        logger.info(f"Saved transcription SRT to: {srt_file_path}")

    return json_file_path


class BaseWhisperWorker:
    """
    Base worker class for Whisper transcription models.
    Handles downloading models locally, caching, loading pipeline,
    and running inference with timestamped output.
    """

    def __init__(
        self,
        model_id: str,
        model_dir: Optional[Union[Path, str]] = None,
        output_dir: Optional[Union[Path, str]] = None,
        device: Optional[Union[str, int]] = None,
        chunk_length_s: int = 30,
        batch_size: int = 8,
    ):
        self.model_id = model_id
        self.model_slug = model_id.split("/")[-1]
        self.model_dir = Path(model_dir) if model_dir else get_default_model_dir(model_id)
        self.output_dir = Path(output_dir) if output_dir else get_default_outputs_dir()
        self.device = device or get_optimal_device()
        self.chunk_length_s = chunk_length_s
        self.batch_size = batch_size
        self._pipeline = None

    def load_pipeline(self):
        """Ensure model is downloaded and initialize the Hugging Face ASR pipeline."""
        if self._pipeline is not None:
            return self._pipeline

        local_path = ensure_model_available(self.model_id, local_dir=self.model_dir)
        logger.info(f"Initializing ASR pipeline for {self.model_id} on device '{self.device}'...")

        try:
            self._pipeline = pipeline(
                "automatic-speech-recognition",
                model=str(local_path),
                tokenizer=str(local_path),
                feature_extractor=str(local_path),
                device=self.device,
                chunk_length_s=self.chunk_length_s,
            )
        except Exception as e:
            # Fall back to CPU if hardware acceleration fails
            if self.device != "cpu":
                logger.warning(
                    f"Failed to load pipeline on device '{self.device}' ({e}). Falling back to 'cpu'."
                )
                self.device = "cpu"
                self._pipeline = pipeline(
                    "automatic-speech-recognition",
                    model=str(local_path),
                    tokenizer=str(local_path),
                    feature_extractor=str(local_path),
                    device="cpu",
                    chunk_length_s=self.chunk_length_s,
                )
            else:
                raise

        return self._pipeline

    def transcribe(
        self,
        audio_path: Union[Path, str],
        save_output: bool = True,
        output_dir: Optional[Union[Path, str]] = None,
        generate_srt: bool = False,
        return_timestamps: bool = True,
        generate_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Transcribe an input audio file and return structured timestamped data.
        """
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file.resolve()}")

        pipe = self.load_pipeline()
        duration = get_audio_duration(audio_file)

        logger.info(f"Transcribing audio file: {audio_file.name} using {self.model_id}...")

        call_kwargs: Dict[str, Any] = {
            "return_timestamps": return_timestamps,
            "batch_size": self.batch_size,
        }
        if generate_kwargs:
            call_kwargs["generate_kwargs"] = generate_kwargs

        raw_output = pipe(str(audio_file), **call_kwargs)

        result = format_transcription_result(
            audio_path=audio_file,
            model_name=self.model_id,
            raw_output=raw_output,
            duration_seconds=duration,
        )

        if save_output:
            target_out = output_dir or self.output_dir
            saved_file = save_transcription_output(
                result_data=result,
                audio_path=audio_file,
                output_dir=target_out,
                model_name=self.model_id,
                save_srt=generate_srt,
            )
            result["output_file"] = str(saved_file.resolve())

        return result
