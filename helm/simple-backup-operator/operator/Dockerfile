FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim

WORKDIR /app

COPY pyproject.toml uv.lock operator.py ./

RUN uv sync --frozen --no-dev

ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "--no-dev", "operator.py"]
