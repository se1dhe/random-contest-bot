#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[1/6] Проверка Alembic"
docker compose exec -T web alembic -c database/alembic.ini current

echo "[2/6] Проверка web"
curl -fsS http://localhost:8000/ >/dev/null

echo "[3/6] Проверка ngrok API"
curl -fsS http://localhost:4040/api/tunnels >/tmp/random-contest-bot-ngrok.json

echo "[4/6] Проверка активного туннеля"
grep -q '"public_url"' /tmp/random-contest-bot-ngrok.json

echo "[5/6] Проверка защиты admin API (ожидаем 403 без auth)"
ADMIN_STATUS="$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/admin/contests)"
if [ "$ADMIN_STATUS" != "403" ]; then
  echo "Ожидали 403 от /api/admin/contests без auth, получили: $ADMIN_STATUS"
  exit 1
fi

echo "[6/6] Проверка защиты publish API (ожидаем 403 без auth)"
PUBLISH_STATUS="$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/publish/contest/1)"
if [ "$PUBLISH_STATUS" != "403" ]; then
  echo "Ожидали 403 от /api/publish/contest/1 без auth, получили: $PUBLISH_STATUS"
  exit 1
fi

echo "Smoke-check пройден"
