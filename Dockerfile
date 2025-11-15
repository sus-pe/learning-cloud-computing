FROM ghcr.io/astral-sh/uv:debian

WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
COPY src ./src

RUN uv sync --frozen
HEALTHCHECK --interval=3s --timeout=2s --start-period=3s --retries=10 \
  CMD curl --fail http://localhost:$PETSTORE_PORT/ || exit 1

# hadolint ignore=DL3025
CMD env; uv run uvicorn petstore:app --host 0.0.0.0 --port ${PETSTORE_PORT}
