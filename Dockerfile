FROM python:3.14-slim

WORKDIR /app

COPY pyproject.toml uv.lock* ./

RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache -r pyproject.toml

COPY main.py ./

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
