FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

WORKDIR /app

COPY pyproject.toml uv.lock* ./

RUN uv sync --frozen --no-dev

COPY main.py ./

FROM python:3.14-slim

WORKDIR /app

COPY --from=builder /app/.venv/lib/python3.14/site-packages /app/site-packages
COPY --from=builder /app/main.py ./

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app/site-packages"

ENTRYPOINT ["python3", "main.py"]
CMD ["backup"]
