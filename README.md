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

## Project Structure

```text
scribby/
├── .env.example                          # Environment variable template
├── .gitignore                            # Git ignore configuration
├── .dockerignore                         # Docker build ignore configuration
├── Dockerfile                            # Production container definition
├── pyproject.toml                        # Project metadata and dependencies
├── uv.lock                               # Deterministic dependency lockfile
├── main.py                               # Application entrypoint
├── README.md                             # Project documentation
├── AGENTS.md                             # AI Agent operational guidelines
└── issues/                               # Issue tracking and resolution history
    ├── templates/
    │   └── issue-resolution-template.md  # Standardized issue resolution report template
    └── issue-1-initialize-codebase.md    # Initialized codebase report
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
