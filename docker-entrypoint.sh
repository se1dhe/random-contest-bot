#!/bin/bash
set -e

echo "Ожидание запуска PostgreSQL..."
until pg_isready -h postgres -U postgres; do
  echo "PostgreSQL недоступен - ожидание..."
  sleep 1
done

echo "PostgreSQL готов!"

echo "Применение миграций БД..."
cd /app
alembic -c database/alembic.ini upgrade head

echo "Запуск приложения..."
exec "$@"

