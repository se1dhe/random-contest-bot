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

# Создание директорий для статики
RUN mkdir -p web/static/css web/static/js web/templates

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV TZ=Europe/Kiev

# Установка часового пояса (должно быть до копирования кода)
RUN ln -snf /usr/share/zoneinfo/Europe/Kiev /etc/localtime && \
    echo "Europe/Kiev" > /etc/timezone && \
    dpkg-reconfigure -f noninteractive tzdata

# Копируем entrypoint скрипт
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Entrypoint для инициализации БД
ENTRYPOINT ["docker-entrypoint.sh"]

# Команда по умолчанию (будет переопределена в docker-compose)
CMD ["python", "-m", "bot.main"]

