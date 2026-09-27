FROM python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db AS builder
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONUTF8=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true POETRY_CACHE_DIR=/app/Temp/poetry \
    TMPDIR=/app/Temp TMP=/app/Temp TEMP=/app/Temp
RUN mkdir -p /app/Temp && pip install --no-cache-dir poetry==2.2.1
COPY . .
RUN poetry install --only main,core --no-root --no-interaction

FROM python:3.12.10-slim-bookworm@sha256:fd95fa221297a88e1cf49c55ec1828edd7c5a428187e67b5d1805692d11588db
WORKDIR /app
ENV PATH=/app/.venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONUTF8=1 \
    TMPDIR=/app/Temp TMP=/app/Temp TEMP=/app/Temp \
    DUSHAN_CONFIG_DIR=/config SERVER_ENV=staging SERVER_ENGINE=granian
COPY --from=builder /app/.venv /app/.venv
COPY . .
RUN mkdir -p /app/Temp/files && chown -R 10001:10001 /app/Temp
USER 10001:10001
EXPOSE 48080
# 容器固定单 worker，由该 worker 持有 Job owner；ASGI 进程直接接收停止信号。
CMD ["python", "-B", "-m", "granian", "--interface", "asgi", "--host", "0.0.0.0", "--port", "48080", "--workers", "1", "--runtime-threads", "1", "--no-access-log", "server.asgi:app"]
