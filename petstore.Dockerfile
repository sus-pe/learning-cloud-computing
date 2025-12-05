FROM ghcr.io/astral-sh/uv:debian
WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
RUN uv python install 3.14
# hadolint ignore=DL3059
RUN uv sync --frozen --no-install-project --no-group internal

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        redis-server=* \
    && rm -rf /var/lib/apt/lists/*

COPY services/ services/
RUN uv sync --frozen

HEALTHCHECK --interval=3s --timeout=2s --start-period=3s --retries=10 \
  CMD curl --fail http://localhost:$PETSTORE_PORT/ || exit 1

CMD ["uv", "run", "petstore"]
