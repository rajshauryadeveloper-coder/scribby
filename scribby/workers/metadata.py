"""Worker metadata and progress tracking system for transcription tasks."""

from __future__ import annotations

import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

# Optional import for transformers streamer base class
try:
    from transformers.generation.streamers import BaseStreamer
except ImportError:  # pragma: no cover
    class BaseStreamer:  # type: ignore
        """Fallback BaseStreamer when transformers is not installed."""

        def put(self, value: Any) -> None:
            pass

        def end(self) -> None:
            pass


@dataclass
class TranscriptionProgress:
    """Represents a live progress snapshot during transcription."""

    status: str  # "starting", "transcribing", "saving", "completed", "failed"
    progress_percentage: float  # 0.0 to 100.0
    words_per_second: float
    words_per_minute: float
    elapsed_time_seconds: float
    word_count: int
    current_text: str = ""
    audio_duration: Optional[float] = None
    processed_duration: Optional[float] = None
    file_path: Optional[str] = None
    metadata_extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert progress snapshot to a dictionary."""
        return asdict(self)


@dataclass
class TranscriptionMetadata:
    """
    Represents the final structured execution metadata of a completed transcription.
    Contains progress percentage, exact execution time, words per second/minute,
    and output file paths.
    """

    progress_percentage: float = 100.0
    words_per_second: float = 0.0
    words_per_minute: float = 0.0
    execution_time_seconds: float = 0.0
    file_path: Optional[str] = None
    output_srt_path: Optional[str] = None
    word_count: int = 0
    audio_duration: Optional[float] = None
    real_time_factor: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to a serializable dictionary with formatted numeric precision."""
        d = asdict(self)
        d["progress_percentage"] = round(self.progress_percentage, 2)
        d["words_per_second"] = round(self.words_per_second, 2)
        d["words_per_minute"] = round(self.words_per_minute, 2)
        d["execution_time_seconds"] = round(self.execution_time_seconds, 3)
        if self.real_time_factor is not None:
            d["real_time_factor"] = round(self.real_time_factor, 2)
        return d


class ProgressTracker:
    """
    Tracks transcription progress, word metrics (live WPS / WPM), and elapsed time.
    Fires callbacks upon status and metric updates.
    """

    def __init__(
        self,
        audio_duration: Optional[float] = None,
        callback: Optional[Callable[[TranscriptionProgress], None]] = None,
    ) -> None:
        self.audio_duration = audio_duration
        self.callback = callback
        self.start_time: float = 0.0
        self.status: str = "pending"
        self.word_count: int = 0
        self.current_text: str = ""
        self.processed_duration: float = 0.0
        self.progress_percentage: float = 0.0
        self.is_completed: bool = False

    def start(self) -> None:
        """Record start timestamp and notify callback of transcription start."""
        self.start_time = time.perf_counter()
        self.status = "starting"
        self.progress_percentage = 0.0
        self.word_count = 0
        self.current_text = ""
        self.is_completed = False
        self._notify()

    def update(
        self,
        status: Optional[str] = None,
        current_text: Optional[str] = None,
        words: Optional[int] = None,
        processed_duration: Optional[float] = None,
        progress_percentage: Optional[float] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update live progress metrics and invoke callback."""
        if self.is_completed:
            return

        if status:
            self.status = status
        elif self.status == "starting":
            self.status = "transcribing"

        if current_text is not None:
            self.current_text = current_text
            if words is None:
                self.word_count = len(current_text.strip().split()) if current_text.strip() else 0

        if words is not None:
            self.word_count = words

        if processed_duration is not None:
            self.processed_duration = processed_duration

        if progress_percentage is not None:
            self.progress_percentage = min(99.9, max(0.0, progress_percentage))
        elif self.audio_duration and self.audio_duration > 0 and self.processed_duration > 0:
            pct = (self.processed_duration / self.audio_duration) * 100.0
            self.progress_percentage = min(99.0, max(0.0, pct))

        self._notify(extra=extra)

    def complete(
        self,
        output_file: Optional[Union[Path, str]] = None,
        output_srt_path: Optional[Union[Path, str]] = None,
        final_text: Optional[str] = None,
    ) -> TranscriptionMetadata:
        """Mark transcription as complete and generate final execution metadata."""
        self.is_completed = True
        self.status = "completed"
        self.progress_percentage = 100.0

        if final_text is not None:
            self.current_text = final_text
            self.word_count = len(final_text.strip().split()) if final_text.strip() else 0

        elapsed = time.perf_counter() - self.start_time if self.start_time > 0 else 0.0
        wps = self.word_count / max(elapsed, 0.001)
        wpm = wps * 60.0

        rtf = (
            round(self.audio_duration / elapsed, 2)
            if (self.audio_duration and self.audio_duration > 0 and elapsed > 0)
            else None
        )

        metadata = TranscriptionMetadata(
            progress_percentage=100.0,
            words_per_second=wps,
            words_per_minute=wpm,
            execution_time_seconds=elapsed,
            file_path=str(Path(output_file).resolve()) if output_file else None,
            output_srt_path=str(Path(output_srt_path).resolve()) if output_srt_path else None,
            word_count=self.word_count,
            audio_duration=self.audio_duration,
            real_time_factor=rtf,
        )

        self._notify(file_path=metadata.file_path)
        return metadata

    def fail(self, error: str) -> None:
        """Mark transcription as failed and emit error status."""
        self.is_completed = True
        self.status = "failed"
        self._notify(extra={"error": error})

    def _notify(
        self,
        file_path: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Build a progress snapshot and execute callback if registered."""
        if not self.callback:
            return

        elapsed = time.perf_counter() - self.start_time if self.start_time > 0 else 0.0
        wps = self.word_count / max(elapsed, 0.001)
        wpm = wps * 60.0

        snapshot = TranscriptionProgress(
            status=self.status,
            progress_percentage=round(self.progress_percentage, 1),
            words_per_second=round(wps, 2),
            words_per_minute=round(wpm, 1),
            elapsed_time_seconds=round(elapsed, 3),
            word_count=self.word_count,
            current_text=self.current_text,
            audio_duration=self.audio_duration,
            processed_duration=round(self.processed_duration, 2) if self.processed_duration else None,
            file_path=file_path,
            metadata_extra=extra or {},
        )

        try:
            self.callback(snapshot)
        except Exception:
            # Prevent user callback issues from breaking transcription pipeline
            pass


class WhisperMetadataStreamer(BaseStreamer):
    """
    Hugging Face generation streamer that intercepts Whisper output tokens in real-time.
    Extracts timestamp tokens for progress tracking and decoded tokens for live WPS/WPM.
    """

    TIMESTAMP_PATTERN = re.compile(r"^<\|(\d+\.\d+)\|\>$")

    def __init__(
        self,
        tokenizer: Any,
        tracker: ProgressTracker,
        chunk_length_s: float = 30.0,
    ) -> None:
        super().__init__()
        self.tokenizer = tokenizer
        self.tracker = tracker
        self.chunk_length_s = chunk_length_s

        self.base_audio_offset: float = 0.0
        self.last_chunk_timestamp: float = 0.0
        self.accumulated_text: str = ""
        self._token_buffer: List[int] = []

    def put(self, value: Any) -> None:
        """Process incoming tokens from model generation."""
        if hasattr(value, "tolist"):
            items = value.tolist()
        elif isinstance(value, (list, tuple)):
            items = list(value)
        else:
            items = [value]

        # Flatten batch dimensions if necessary
        flat_tokens: List[int] = []
        for item in items:
            if isinstance(item, list):
                flat_tokens.extend(item)
            else:
                flat_tokens.append(int(item))

        new_text_segments: List[str] = []

        for tid in flat_tokens:
            # Check for timestamp tokens
            tok_str = self.tokenizer.convert_ids_to_tokens(tid)
            if tok_str:
                match = self.TIMESTAMP_PATTERN.match(tok_str)
                if match:
                    chunk_ts = float(match.group(1))
                    if chunk_ts < self.last_chunk_timestamp and self.last_chunk_timestamp > 0:
                        # New chunk boundary detected
                        self.base_audio_offset += max(self.last_chunk_timestamp, self.chunk_length_s)

                    self.last_chunk_timestamp = chunk_ts
                    current_processed = self.base_audio_offset + chunk_ts
                    self.tracker.update(processed_duration=current_processed)
                    continue

            # Decode normal token pieces
            decoded_piece = self.tokenizer.decode([tid], skip_special_tokens=True)
            if decoded_piece:
                new_text_segments.append(decoded_piece)

        if new_text_segments:
            self.accumulated_text += "".join(new_text_segments)
            self.tracker.update(current_text=self.accumulated_text.strip())

    def end(self) -> None:
        """Signal that generation for the current chunk has finished."""
        if self.last_chunk_timestamp > 0:
            self.base_audio_offset += self.last_chunk_timestamp
            self.last_chunk_timestamp = 0.0


class ConsoleProgressReporter:
    """
    Terminal output reporter providing live progress, live WPS/WPM updates,
    and a clean summary upon completion.
    """

    def __init__(self, quiet: bool = False, is_tty: Optional[bool] = None) -> None:
        self.quiet = quiet
        self.is_tty = is_tty if is_tty is not None else sys.stdout.isatty()
        self._last_line_len = 0

    def __call__(self, progress: TranscriptionProgress) -> None:
        """Callback handler for live progress events."""
        if self.quiet:
            return

        if progress.status in ("starting", "transcribing", "saving"):
            msg = (
                f"\r[Scribby Progress] {progress.progress_percentage:5.1f}% | "
                f"{progress.words_per_second:5.1f} words/s ({progress.words_per_minute:6.1f} wpm) | "
                f"Elapsed: {progress.elapsed_time_seconds:5.2f}s | "
                f"Words: {progress.word_count:4d}"
            )
            if self.is_tty:
                sys.stdout.write(msg.ljust(self._last_line_len))
                sys.stdout.flush()
                self._last_line_len = len(msg)
            else:
                # Log periodically or at key milestones when not in TTY
                pass

        elif progress.status == "completed":
            if self.is_tty:
                sys.stdout.write("\r" + " " * self._last_line_len + "\r")
                sys.stdout.flush()
