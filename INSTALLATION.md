# Инструкция по установке и запуску

## Требования

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker и Docker Compose (опционально, для контейнеризации)
- Ngrok (для туннелирования, если используется)

## Установка

### 1. Клонирование проекта

```bash
git clone <repository>
cd random-contest-bot
```

### 2. Настройка конфигурации

Отредактируйте файл `config.ini`:

```ini
[telegram]
BOT_TOKEN=your_bot_token_here  # Получить у @BotFather
ADMIN_ID=your_admin_id_here    # Получить у @userinfobot

[database]
DB_HOST=localhost
DB_PORT=5432
DB_NAME=contest_bot
DB_USER=postgres
DB_PASSWORD=postgres

[ngrok]
ENABLED=true
NGROK_AUTHTOKEN=your_ngrok_token
NGROK_DOMAIN=your-domain.ngrok-free.app
NGROK_REGION=eu
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка базы данных

Создайте базу данных PostgreSQL:

```bash
createdb contest_bot
```

Примените миграции:

```bash
cd database
alembic upgrade head
```

### 5. Запуск через Docker (рекомендуется)

```bash
docker-compose up -d
```

Или используйте скрипт:

```bash
./run.sh
```

### 6. Запуск локально

В одном терминале:

```bash
python -m bot.main
```

В другом терминале:

```bash
python -m web.main
```

## Использование

### Для администратора

1. Откройте бота в Telegram и отправьте `/start`
2. Откройте админ-панель через вебапп: `https://your-domain.ngrok-free.app/admin`
3. Добавьте каналы в разделе "Каналы"
4. Создайте конкурс в разделе "Создать конкурс"
5. Опубликуйте конкурс в канале
6. После окончания конкурса завершите его и опубликуйте результаты

### Для пользователей

1. Перейдите в канал с конкурсом
2. Нажмите кнопку "Зарегистрироваться" в сообщении о конкурсе
3. Подпишитесь на необходимые каналы (если требуется)
4. Зарегистрируйтесь в конкурсе
5. После подведения итогов просмотрите результаты через кнопку "Итоги"

## Структура проекта

```
random-contest-bot/
├── bot/                    # Telegram бот
│   ├── handlers/          # Обработчики команд
│   ├── services/          # Бизнес-логика
│   └── main.py            # Точка входа бота
├── web/                   # FastAPI веб-сервер
│   ├── api/               # API роуты
│   ├── templates/         # HTML шаблоны
│   ├── static/            # CSS, JS, изображения
│   └── main.py            # Точка входа веб-сервера
├── database/              # База данных
│   ├── models/           # SQLAlchemy модели
│   └── migrations/       # Alembic миграции
├── shared/                # Общий код
│   ├── config/           # Конфигурация
│   ├── services/         # Общие сервисы
│   └── utils/            # Утилиты
├── config.ini             # Конфигурация приложения
├── docker-compose.yml      # Docker Compose конфигурация
└── requirements.txt       # Python зависимости
```

## API Endpoints

### Публичные

- `GET /api/contests/{contest_id}` - Получить информацию о конкурсе
- `GET /api/contests/{contest_id}/check-subscription` - Проверить подписки
- `POST /api/contests/{contest_id}/register` - Зарегистрироваться в конкурсе
- `GET /api/contests/{contest_id}/winners` - Получить победителей

### Административные (требуют авторизации)

- `GET /api/admin/channels` - Список каналов
- `POST /api/admin/channels` - Создать канал
- `DELETE /api/admin/channels/{channel_id}` - Удалить канал
- `GET /api/admin/contests` - Список конкурсов
- `POST /api/admin/contests` - Создать конкурс
- `POST /api/admin/contests/{contest_id}/draw` - Провести розыгрыш
- `POST /api/publish/contest/{contest_id}` - Опубликовать конкурс
- `POST /api/publish/results/{contest_id}` - Опубликовать результаты

## Вебаппы

- `/register?contest_id={id}` - Регистрация в конкурсе
- `/results?contest_id={id}` - Просмотр результатов
- `/admin` - Админ-панель

## Troubleshooting

### Проблемы с подключением к БД

Проверьте настройки в `config.ini` и убедитесь, что PostgreSQL запущен.

### Проблемы с ngrok

Убедитесь, что токен ngrok указан правильно и домен доступен.

### Проблемы с публикацией в канале

Убедитесь, что бот добавлен в канал как администратор.

## Лицензия

MIT

