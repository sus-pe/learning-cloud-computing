FROM ghcr.io/astral-sh/uv:debian
WORKDIR /app

RUN uv python install 3.14

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-install-project --no-group internal

COPY services/ services/
COPY src/ src/
RUN uv sync --frozen

