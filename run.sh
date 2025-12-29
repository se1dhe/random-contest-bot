#!/bin/bash

# Скрипт для запуска проекта

echo "Запуск проекта Contest Bot..."

# Проверка наличия config.ini
if [ ! -f "config.ini" ]; then
    echo "Ошибка: файл config.ini не найден!"
    exit 1
fi

# Запуск через docker-compose
if command -v docker-compose &> /dev/null; then
    echo "Запуск через Docker Compose..."
    docker-compose up -d
    
    echo "Ожидание запуска сервисов..."
    sleep 5
    
    echo "Применение миграций БД..."
    docker-compose exec bot alembic upgrade head
    
    echo "Проект запущен!"
    echo "Бот: запущен в контейнере"
    echo "Веб-сервер: http://localhost:8000"
    echo "Для просмотра логов: docker-compose logs -f"
else
    echo "Docker Compose не установлен. Запуск локально..."
    
    # Локальный запуск (требует установленных зависимостей)
    echo "Применение миграций БД..."
    alembic upgrade head
    
    echo "Запуск бота в фоне..."
    python -m bot.main &
    
    echo "Запуск веб-сервера..."
    python -m web.main
fi

