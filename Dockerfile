FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system deps (curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies first (cache layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --no-install-project

# Copy source
COPY src/ src/
COPY alembic.ini ./
COPY README.md ./

# Install project
RUN uv sync --no-dev

EXPOSE 8000

# Default: run the API server
CMD ["uv", "run", "uvicorn", "helix.main:app", "--host", "0.0.0.0", "--port", "8000"]
