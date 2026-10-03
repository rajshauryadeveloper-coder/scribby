"""Convenience root wrapper for Whisper Medium worker."""

import sys
from pathlib import Path

# Add repo root to sys.path
repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from scribby.workers.whisper_medium_worker import (
    WhisperMediumWorker,
    main,
    transcribe_audio,
)

__all__ = ["WhisperMediumWorker", "transcribe_audio", "main"]

if __name__ == "__main__":
    sys.exit(main())
