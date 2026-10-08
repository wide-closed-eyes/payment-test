#!/bin/bash


apply_migrations() {
    echo "Применение миграций..."
    if alembic upgrade head; then
        return 0
    else
        echo "Ошибка при применении миграций"
        return 1
    fi
}

set -e

if apply_migrations; then
    exec uvicorn app:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers 1 \
        --loop asyncio
else
    exit 1
fi