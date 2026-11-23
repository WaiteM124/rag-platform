FROM node:20-alpine AS webbuild
WORKDIR /web
COPY web/package.json ./
RUN npm install
COPY web/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app
COPY pyproject.toml README.md ./
COPY ingest ./ingest
COPY app ./app
COPY collections ./collections
COPY config ./config
COPY evals ./evals
RUN pip install --no-cache-dir .

COPY --from=webbuild /web/dist /app/static
ENV STATIC_DIR=/app/static
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]