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
- **Database-Ready Timestamped Output:** Transcriptions are structured into JSON files under `outputs/` with audio metadata, total duration, full text, and timestamped segments (`id`, `start`, `end`, `text`).
- **Pipeline & CLI Ready:** Can be used either as standalone CLI commands or imported directly into Python processing pipelines.
- **Optional Subtitles:** Can export `.srt` subtitle files alongside JSON via `--srt`.

### Usage

#### 1. CLI Execution
```bash
# Using Whisper Base
uv run python workers/whisper_base_worker.py path/to/audio.wav

# Using Whisper Medium with subtitle export
uv run python workers/whisper_medium_worker.py path/to/audio.mp3 --srt --output-dir outputs/
```

#### 2. Pipeline Integration (Python API)
```python
from scribby.workers.whisper_base_worker import WhisperBaseWorker, transcribe_audio

# One-liner convenience
result = transcribe_audio("audio.wav", output_dir="outputs/", generate_srt=True)
print(result["text"])
print(result["segments"])

# Or with worker instance
worker = WhisperBaseWorker()
result = worker.transcribe("audio.mp3")
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
├── .gitignore                            # Git ignore configuration (models & outputs ignored)
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
│       ├── whisper_base_worker.py        # openai/whisper-base worker
│       └── whisper_medium_worker.py      # openai/whisper-medium worker
├── workers/                              # Root convenience accessors
│   ├── __init__.py
│   ├── whisper_base_worker.py
│   └── whisper_medium_worker.py
├── tests/                                # Test suite
│   ├── test_cli.py
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
    └── issue-3-create-transcription-workers.md # Transcription workers report
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
