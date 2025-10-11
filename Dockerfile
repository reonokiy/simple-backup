FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

WORKDIR /app

COPY pyproject.toml uv.lock* ./

RUN uv sync --frozen --no-dev

COPY main.py ./

FROM gcr.io/distroless/python3-debian12:nonroot

WORKDIR /app

COPY --from=builder /app/.venv/lib/python3.14/site-packages /app/site-packages
COPY --from=builder /app/main.py ./

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app/site-packages"

CMD ["/usr/bin/python3", "main.py"]
