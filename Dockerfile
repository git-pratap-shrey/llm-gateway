FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies (no project install yet, just deps)
RUN uv sync --frozen --no-install-project

# Copy the rest of the source
COPY . .

# Install the project itself
RUN uv sync --frozen
