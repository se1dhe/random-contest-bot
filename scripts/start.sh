#!/bin/bash
set -e

case "${SERVICE_TYPE:-bot}" in
  web)
    exec python -m web.main
    ;;
  bot)
    exec python -m bot.main
    ;;
  *)
    echo "Unknown SERVICE_TYPE: ${SERVICE_TYPE}" >&2
    exit 1
    ;;
esac
