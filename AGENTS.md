# AGENTS.md - Agent Operating Guidelines for Scribby

This document establishes the official instructions, standards, and workflow protocols for AI coding agents operating in the `scribby` repository. All agents must follow these guidelines strictly.

---

## 1. Core Principles

1. **Deterministic Dependency Management:** Always use `uv`. Never run bare `pip` or modify environments outside of `uv`.
2. **Feature Branching:** Never commit directly to `main`. Every unit of work or issue must have its own branch.
3. **Mandatory Issue Resolution Logging:** Every issue must be tracked with a structured resolution report under `issues/` and posted back to the GitHub issue before closure.
4. **Zero Secret Leakage:** Never commit secrets, tokens, or local `.env` files. Always keep `.env.example` in sync with any required environment variables.
5. **Zero Model Weight Leakage:** Never commit model binaries (`*.safetensors`, `*.bin`, etc.) or local model caches (`models/`) to git.
6. **Rigorous Verification:** Never conclude a task without executing and verifying the changes.

---

## 2. Package & Environment Management (`uv`)

- **Add Dependencies:**
  ```bash
  uv add <package_name>
  uv add --dev <dev_package_name>
  ```
- **Sync Dependencies:**
  ```bash
  uv sync
  ```
- **Execute Code:**
  ```bash
  uv run <command_or_script>
  ```
- **Python Version:** The repository targets Python `>=3.12`. Do not introduce dependencies incompatible with this version range.

---

## 3. Git & Branching Strategy

1. **Branch Naming:**
   Create feature branches named with the issue number and a brief slug:
   ```bash
   issue-<number>-<short-description>
   # Example: issue-1-initialize-codebase
   ```
2. **Commit Messages:**
   Use clear, conventional commit messages:
   - `feat: add ...`
   - `fix: resolve ...`
   - `docs: update ...`
   - `refactor: ...`
3. **Pull Requests:**
   Always open a PR against `main` upon finishing implementation and verification.

---

## 4. Mandatory Issue Resolution Protocol

Whenever assigned to or working on a GitHub issue, follow this standardized cycle:

### Step 1: Branch Creation
Create and switch to `issue-<number>-<description>`.

### Step 2: Implementation & Verification
Implement the necessary changes and verify them thoroughly using `uv run` and applicable test commands.

### Step 3: Issue Resolution Report
Create a new report in the `issues/` directory:
- Path: `issues/issue-<number>-<description>.md`
- Source Template: `issues/templates/issue-resolution-template.md`

The report must document:
- **Metadata:** Issue link, date & Indian Standard timestamp down to the second (`YYYY-MM-DD HH:MM:SS IST`), branch, PR.
- **Issue Description:** Summary of the requirements and acceptance criteria.
- **Solution Overview:** Design and architecture of the implementation.
- **Changed Files:** Detailed table of created, modified, or deleted files.
- **Challenges & Mistakes:** Explicitly document any mistakes, build errors, or unexpected hurdles encountered and how they were rectified.
- **Verification & Testing:** Exact commands executed and their output evidence.

### Step 4: GitHub Issue Comment
Post the exact Markdown content of the resolution report as a comment on the GitHub issue prior to closing or marking it complete.

---

## 5. Environment Configurations

- `.env.example`: Committed template showing all necessary keys and sensible default or dummy values.
- `.env`: Ignored in git. Stores local runtime values.
- When introducing a new environment variable in the application, **you must update `.env.example` immediately**.

---

## 6. Docker & Container Standards

- The `Dockerfile` must utilize multi-stage or slim base images with `uv` for reproducible builds.
- Ensure any added assets or ignore rules are reflected in `.dockerignore`.
- Avoid hardcoding host paths or sensitive variables into Docker images.

---

## 7. Model & Heavy Artifact Management

- **Local Model Caching:** AI models must download locally on their initial run and subsequently load offline from disk to eliminate redundant network traffic.
- **Selective Downloads:** When utilizing `snapshot_download` from `huggingface_hub`, always configure `ignore_patterns` to skip unused framework binaries (`*.msgpack`, `*.h5`, `*.ot`, etc.) to prevent multi-gigabyte bloat.
- **Git & Container Exclusion:** Model weight files (`*.safetensors`, `*.bin`, `*.pt`, `*.onnx`) and model directories (`models/`) must remain strictly excluded in `.gitignore` and `.dockerignore`.

---

## 8. Output Artifact Organization

- **Categorized Subfolders:** Outputs must be organized by task domain into structured subfolders under `outputs/` (e.g. `outputs/transcriptions/`, `outputs/summaries/`).
- **Single Representation Rule:** When staging outputs in git for verification, keep exactly one clean copy of each output format (e.g., one `.json` and one `.srt` per sample), avoiding repeated local test churn.

