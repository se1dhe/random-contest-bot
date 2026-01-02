# Инструкция по развертыванию

Этот гайд поможет вам развернуть Random Contest Bot на Linux сервере с использованием Docker.

## Требования
*   **Docker** и **Docker Compose** должны быть установлены.
*   **Токен Telegram Бота** (получается у @BotFather).
*   *Опционально*: **Учетные данные YouTube Data API** (Client ID/Secret) для проверки подписок YouTube.

## Конфигурация

Приложение настраивается через файл `config.ini` в корневой директории проекта.

1.  **Клонируйте репозиторий**:
    ```bash
    git clone <repository_url>
    cd random-contest-bot
    ```

2.  **Создайте `config.ini`**:
    Создайте файл с именем `config.ini` в корневой папке и вставьте следующее содержимое:

    ```ini
    [telegram]
    BOT_TOKEN = 123456789:ABCdefGHIjklMNOpqrsTUVwxyz
    ADMIN_ID = 123456789

    [database]
    DB_HOST = db
    DB_PORT = 5432
    DB_NAME = contest_bot
    DB_USER = contest_user
    DB_PASSWORD = contest_password

    [redis]
    REDIS_HOST = redis
    REDIS_PORT = 6379
    REDIS_PASSWORD = 
    REDIS_DB = 0

    [web]
    WEB_PORT = 8000
    WEB_HOST = 0.0.0.0
    SECRET_KEY = your-secret-session-key-change-me
    # HTTPS URL, где размещен ваш бот (обязательно для Telegram Web App)
    WEBAPP_URL = https://your-domain.com

    [youtube]
    # Опционально: Для проверки подписки YouTube
    API_KEY = 
    CLIENT_ID = 
    CLIENT_SECRET = 

    [ngrok]
    # Опционально: Только для локальной разработки
    ENABLED = false
    NGROK_AUTHTOKEN = 
    NGROK_DOMAIN = 
    NGROK_REGION = eu
    ```

3.  **Безопасность**:
    Убедитесь, что `config.ini` добавлен в `.gitignore`, если вы используете публичный репозиторий.

## Запуск с Docker

Мы используем Docker Compose для оркестрации сервисов (Бот/API, PostgreSQL, Redis).

1.  **Сборка и запуск**:
    ```bash
    docker-compose up -d --build
    ```

2.  **Проверка логов**:
    ```bash
    docker-compose logs -f
    ```

3.  **Миграции Базы Данных**:
    Контейнер настроен на автоматический запуск миграций (Alembic) при старте. Вы можете проверить это в логах.

## Настройка Nginx (Для продакшена)

Для продакшена рекомендуется использовать Nginx как reverse proxy для обработки SSL.

1.  Установите Nginx и Certbot.
2.  Настройте Nginx на проксирование запросов к `http://localhost:8000`.
3.  Получите SSL сертификат:
    ```bash
    certbot --nginx -d your-domain.com
    ```
4.  Обновите `WEBAPP_URL` в `config.ini` на `https://your-domain.com`.
5.  Перезагрузите веб-сервис:
    ```bash
    docker-compose restart web
    ```

## Устранение неполадок

*   **Ошибка WebApp (400 Bad Request)**: Обычно означает, что `WEBAPP_URL` не совпадает с доменом, обслуживающим приложение, или SSL сертификат недействителен. Telegram требует HTTPS.
*   **Ошибка подключения к БД**: Убедитесь, что настройки `[database]` в `config.ini` совпадают с переменными окружения в `docker-compose.yml` (если вы их меняли).
*   **Отсутствуют статические файлы**: Если Админ-панель выглядит сломанной, пересоберите фронтенд:
    ```bash
    docker-compose build web
    docker-compose up -d web
    ```
