# Stage 1: Builder
FROM python:3.12-slim as builder

WORKDIR /app

RUN pip install --no-cache-dir "poetry==2.1.2"

COPY poetry.lock pyproject.toml ./

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# Stage 2: Production
FROM python:3.12-slim

WORKDIR /app

# Копируем Python пакеты из builder
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=builder /usr/local/bin/alembic /usr/local/bin/alembic
COPY --from=builder /usr/local/bin/poetry /usr/local/bin/poetry

COPY bin/ ./bin/
COPY alembic.ini .
COPY alembic/ ./alembic/
COPY app.py .
COPY src/ ./src/

# Настройка безопасности
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chown -R appuser:appuser /app \
    && chmod 755 ./bin/entrypoint.sh \
    # Очищаем кэш и временные файлы
    && find /app -name "*.pyc" -delete \
    && find /app -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true \
    && python -m compileall -q /app || true

USER appuser

EXPOSE 8000

ENTRYPOINT [ "./bin/entrypoint.sh" ]