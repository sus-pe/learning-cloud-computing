FROM ghcr.io/astral-sh/uv:debian
WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        redis-server=* \
    && rm -rf /var/lib/apt/lists/*

COPY src ./src
RUN uv sync --frozen

HEALTHCHECK --interval=3s --timeout=2s --start-period=3s --retries=10 \
  CMD curl --fail http://localhost:$PETSTORE_PORT/ || exit 1

CMD ["uv", "run", "petstore"]
