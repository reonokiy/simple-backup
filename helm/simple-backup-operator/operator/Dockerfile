FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

COPY operator.py ./

ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "--no-dev", "operator.py"]
