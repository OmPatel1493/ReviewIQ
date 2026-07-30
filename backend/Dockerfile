# syntax=docker/dockerfile:1
#
# Backend image, built with uv for fast, reproducible installs.
# Multi-stage keeps the final image slim: build deps stay in the builder layer.

FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copy the standalone uv binary from Astral's published image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# 1) Install dependencies first (cached layer). Copy only the manifest so this
#    layer is invalidated only when dependencies change, not on every code edit.
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project

# 2) Copy the application code and finish the install.
COPY . .
RUN uv sync --no-dev

EXPOSE 8000

# Run under uvicorn. In production you'd front this with multiple workers /
# gunicorn; for local + small deploys a single uvicorn process is fine.
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
