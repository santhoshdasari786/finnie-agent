# syntax=docker/dockerfile:1

FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Pull the uv binary from its official distroless image instead of pip-installing it.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first, in their own layer, so editing application code
# doesn't invalidate the dependency cache on every rebuild.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Now copy the rest of the project and sync again (fast — deps are already cached).
COPY . .
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Run as an ordinary user. The vector store lives in a volume mounted at /app/.vectorstore.
RUN useradd --create-home --uid 1000 finnie \
 && mkdir -p /app/.vectorstore && chown -R finnie:finnie /app/.vectorstore
USER finnie

EXPOSE 8000

# The slim image has no curl, so the check uses Python's standard library.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
