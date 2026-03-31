FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install dependencies first (cache layer)
COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

# Copy source
COPY src/ src/
COPY docs/ docs/
COPY CLAUDE.md ./

# Install project
RUN uv sync --no-dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "helix.main:app", "--host", "0.0.0.0", "--port", "8000"]
