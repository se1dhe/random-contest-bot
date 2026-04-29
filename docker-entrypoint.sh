#!/bin/bash
set -e

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  echo "Ожидание PostgreSQL и применение миграций БД..."
  cd /app
  python scripts/run_migrations.py
fi

echo "Запуск приложения..."
exec "$@"
