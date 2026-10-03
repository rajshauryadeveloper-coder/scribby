# Scribby

Scribby is a modern Python workspace designed for AI agents and rapid application development.

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (v0.5.0 or later recommended)
- Python 3.12 or newer
- [Docker](https://www.docker.com/) (optional, for containerized deployments)

---

## Quickstart

### 1. Clone the repository
```bash
git clone https://github.com/rajshauryadeveloper-coder/scribby.git
cd scribby
```

### 2. Environment Configuration
Copy the template environment file to `.env`:
```bash
cp .env.example .env
```
Update `.env` with your desired configuration settings.

### 3. Install Dependencies
Scribby uses `uv` for fast, deterministic dependency management:
```bash
uv sync
```
This automatically creates a virtual environment at `.venv` and installs all locked dependencies.

### 4. Run the Application
```bash
uv run main.py
```

---

## Docker Deployment

Build and run Scribby inside a lightweight Docker container:

```bash
# Build the Docker image
docker build -t scribby:latest .

# Run the container with your environment configuration
docker run --rm --env-file .env scribby:latest
```

---

## Transcription Workers

Scribby provides production-ready speech-to-text workers powered by Hugging Face Transformers and Whisper models:
- **Whisper Base Worker** (`openai/whisper-base`): Lightweight and fast speech recognition.
- **Whisper Medium Worker** (`openai/whisper-medium`): High-accuracy, rich multilingual speech recognition.

### Key Features
- **Local Model Caching:** Models are downloaded once to `models/` (gitignored) on the first run and subsequently loaded offline from disk without re-downloading.
- **Worker Metadata & Progress Tracking:** Real-time progress monitoring provides:
  - Progress percentage ($0.0\%$ to $100.0\%$)
  - Live and overall Words Per Second (WPS) and Words Per Minute (WPM)
  - Exact time taken to complete the transcription
  - Saved output file paths (`.json` and optional `.srt`)
- **Database-Ready Timestamped Output:** Transcriptions are structured into JSON files under `outputs/` with audio metadata, total duration, full text, timestamped segments (`id`, `start`, `end`, `text`), and an execution `metadata` dictionary.
- **Pipeline & CLI Ready:** Can be used either as standalone CLI commands (with interactive live progress or `--quiet`) or imported directly into Python processing pipelines with custom `progress_callback` handlers.
- **Optional Subtitles:** Can export `.srt` subtitle files alongside JSON via `--srt`.

### Usage

#### 1. CLI Execution
```bash
# Using Whisper Base (with live progress tracking)
uv run python workers/whisper_base_worker.py path/to/audio.wav

# Using Whisper Medium with subtitle export and quiet mode
uv run python workers/whisper_medium_worker.py path/to/audio.mp3 --srt --output-dir outputs/ --quiet
```

#### 2. Pipeline Integration (Python API)
```python
from scribby.workers.whisper_base_worker import WhisperBaseWorker, transcribe_audio
from scribby.workers.metadata import TranscriptionProgress

# Optional live progress callback
def on_progress(p: TranscriptionProgress):
    print(f"[{p.progress_percentage:.1f}%] {p.words_per_second:.1f} words/s ({p.words_per_minute:.1f} wpm) | Elapsed: {p.elapsed_time_seconds:.2f}s")

# One-liner convenience with callback
result = transcribe_audio(
    "audio.wav",
    output_dir="outputs/",
    generate_srt=True,
    progress_callback=on_progress,
)
print("Execution Metadata:", result["metadata"])
print("Full Text:", result["text"])
```

### Running Tests
```bash
uv run pytest
```

---

## Project Structure

```text
scribby/
├── .env.example                          # Environment variable template
├── .gitignore                            # Git ignore configuration (models ignored)
├── .dockerignore                         # Docker build ignore configuration
├── Dockerfile                            # Production container definition
├── pyproject.toml                        # Project metadata and dependencies
├── uv.lock                               # Deterministic dependency lockfile
├── main.py                               # Application entrypoint
├── scribby/                              # Core package
│   ├── __init__.py
│   └── workers/                          # Transcription workers
│       ├── __init__.py
│       ├── base.py                       # Base worker, model caching & output formatters
│       ├── metadata.py                   # Progress tracking, WPS/WPM calculation & streamers
│       ├── whisper_base_worker.py        # openai/whisper-base worker
│       └── whisper_medium_worker.py      # openai/whisper-medium worker
├── workers/                              # Root convenience accessors
│   ├── __init__.py
│   ├── whisper_base_worker.py
│   └── whisper_medium_worker.py
├── outputs/                              # Application outputs and artifacts
│   ├── transcriptions/                   # Speech-to-text transcriptions (.json, .srt)
│   ├── summaries/                        # Future summaries output (.gitkeep)
│   ├── translations/                     # Future translations output (.gitkeep)
│   ├── diarization/                      # Future speaker diarization output (.gitkeep)
│   └── audio/                            # Future generated audio output (.gitkeep)
├── tests/                                # Test suite
│   ├── test_cli.py
│   ├── test_metadata.py
│   ├── test_model_manager.py
│   ├── test_output_formatter.py
│   ├── test_whisper_base_worker.py
│   └── test_whisper_medium_worker.py
├── README.md                             # Project documentation
├── AGENTS.md                             # AI Agent operational guidelines
└── issues/                               # Issue tracking and resolution history
    ├── templates/
    │   └── issue-resolution-template.md  # Standardized issue resolution report template
    ├── issue-1-initialize-codebase.md    # Initialized codebase report
    ├── issue-3-create-transcription-workers.md # Transcription workers report
    └── issue-6-worker-metadata.md        # Worker metadata system report
```

---

## Development Workflow

- **Managing Dependencies:** Use `uv add <package>` to add dependencies and `uv remove <package>` to remove them.
- **Running Tools:** Execute commands within the environment using `uv run <command>`.
- **Issue Resolution Protocol:**
  Whenever working on an issue:
  1. Create a dedicated branch: `git checkout -b issue-<number>-<description>`
  2. Implement and verify the changes.
  3. Create an issue report under `issues/` utilizing `issues/templates/issue-resolution-template.md`.
  4. Post the completed report as a comment on the GitHub issue upon closing.
  5. Open a Pull Request back to `main`.

For detailed agent behavioral instructions and rules, see [AGENTS.md](AGENTS.md).
