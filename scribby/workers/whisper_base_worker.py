"""Whisper Base Transcription Worker using 'openai/whisper-base'."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

# Support running directly as a script without explicit PYTHONPATH set
if __name__ == "__main__" and __package__ is None:
    repo_root = Path(__file__).resolve().parent.parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from scribby.workers.base import BaseWhisperWorker
from scribby.workers.metadata import ConsoleProgressReporter, TranscriptionProgress

logger = logging.getLogger("scribby.workers.whisper_base")


class WhisperBaseWorker(BaseWhisperWorker):
    """
    Transcription worker specialized for the 'openai/whisper-base' model.
    Optimized for fast inference and lightweight resource consumption.
    """

    DEFAULT_MODEL_ID = "openai/whisper-base"

    def __init__(
        self,
        model_dir: Optional[Union[Path, str]] = None,
        output_dir: Optional[Union[Path, str]] = None,
        device: Optional[Union[str, int]] = None,
        chunk_length_s: int = 30,
        batch_size: int = 8,
    ):
        super().__init__(
            model_id=self.DEFAULT_MODEL_ID,
            model_dir=model_dir,
            output_dir=output_dir,
            device=device,
            chunk_length_s=chunk_length_s,
            batch_size=batch_size,
        )


def transcribe_audio(
    audio_path: Union[Path, str],
    output_dir: Optional[Union[Path, str]] = None,
    save_output: bool = True,
    generate_srt: bool = False,
    device: Optional[Union[str, int]] = None,
    progress_callback: Optional[Callable[[TranscriptionProgress], None]] = None,
) -> Dict[str, Any]:
    """
    Convenience function to transcribe an audio file using Whisper Base.
    Can be easily imported and called in external pipelines.
    """
    worker = WhisperBaseWorker(output_dir=output_dir, device=device)
    return worker.transcribe(
        audio_path=audio_path,
        save_output=save_output,
        output_dir=output_dir,
        generate_srt=generate_srt,
        progress_callback=progress_callback,
    )


def main() -> int:
    """CLI entrypoint for Whisper Base transcription worker."""
    parser = argparse.ArgumentParser(
        description="Scribby Whisper Base Worker - Transcribe audio using openai/whisper-base",
    )
    parser.add_argument(
        "audio",
        type=str,
        help="Path to the audio file to transcribe",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=None,
        help="Custom directory to store output files (default: outputs/)",
    )
    parser.add_argument(
        "--srt",
        action="store_true",
        help="Also export subtitle format (.srt) alongside JSON",
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Inference device: 'cpu', 'cuda', 'mps' (default: auto-detected)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Suppress live progress updates in console",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"Error: Audio file not found at {audio_path.resolve()}", file=sys.stderr)
        return 1

    try:
        reporter = ConsoleProgressReporter(quiet=args.quiet)
        worker = WhisperBaseWorker(output_dir=args.output_dir, device=args.device)
        result = worker.transcribe(
            audio_path=audio_path,
            save_output=True,
            generate_srt=args.srt,
            progress_callback=reporter,
        )
        meta = result.get("metadata", {})
        print("\n=== Transcription Complete ===")
        print(f"Model: {result['model']}")
        if "execution_time_seconds" in meta:
            print(f"Execution Time: {meta['execution_time_seconds']:.2f}s")
        if "words_per_second" in meta:
            print(f"Speed: {meta['words_per_second']:.1f} words/s ({meta.get('words_per_minute', 0):.1f} wpm)")
        if "progress_percentage" in meta:
            print(f"Progress: {meta['progress_percentage']:.1f}%")
        print(f"Output File: {result.get('output_file')}")
        if meta.get("output_srt_path"):
            print(f"SRT File: {meta.get('output_srt_path')}")
        print(f"Full Text:\n{result['text']}\n")
        return 0
    except Exception as e:
        logger.error(f"Failed to transcribe: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
