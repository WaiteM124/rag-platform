FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    pandoc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY ingest ./ingest
COPY collections ./collections
COPY config ./config
COPY app ./app

RUN pip install --no-cache-dir .

ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python", "-m", "ingest"]