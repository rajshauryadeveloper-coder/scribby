# Use an official lightweight Python image
FROM python:3.12-slim

# Set environment variables for Python and uv
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install uv from the official pre-built image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Copy dependency definition and lockfile first for optimal layer caching
COPY pyproject.toml uv.lock ./

# Install project dependencies
RUN uv sync --frozen --no-install-project --no-dev

# Copy project files into container
COPY . .

# Place the virtual environment executables at the beginning of PATH
ENV PATH="/app/.venv/bin:$PATH"

# Default entrypoint
CMD ["python", "main.py"]
