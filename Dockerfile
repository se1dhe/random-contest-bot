FROM node:20-slim AS frontend-builder

WORKDIR /app/web/frontend

COPY web/frontend/package*.json ./
RUN npm ci

COPY web/frontend ./
RUN npm run build


FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .
COPY --from=frontend-builder /app/web/static/dist ./web/static/dist

# Создание директорий для статики и загружаемых файлов
RUN mkdir -p web/static/css web/static/js web/templates web/static/dist /app/uploads

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV TZ=Europe/Kyiv

# Установка часового пояса (должно быть до копирования кода)
RUN ln -snf /usr/share/zoneinfo/Europe/Kyiv /etc/localtime && \
    echo "Europe/Kyiv" > /etc/timezone && \
    dpkg-reconfigure -f noninteractive tzdata

# Копируем entrypoint скрипт
COPY docker-entrypoint.sh /usr/local/bin/
COPY scripts/start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh /usr/local/bin/start.sh

# Entrypoint для инициализации БД
ENTRYPOINT ["docker-entrypoint.sh"]

# Команда по умолчанию выбирает bot/web по SERVICE_TYPE
CMD ["start.sh"]
