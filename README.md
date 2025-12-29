# Telegram Contest Bot

Бот для проведения конкурсов в Telegram каналах с веб-интерфейсом для администрирования и участия.

## Технологии

- **Python 3.11+**
- **aiogram 3.4** - Telegram Bot Framework
- **FastAPI** - Веб-фреймворк для вебаппов
- **PostgreSQL** - База данных
- **Redis** - Кеширование и сессии
- **Tailwind CSS** - Стилизация вебаппов
- **Docker** - Контейнеризация

## Архитектура

Проект следует принципам Clean Architecture:

```
contest-bot/
├── bot/                    # Telegram бот (aiogram)
│   ├── handlers/           # Обработчики команд и сообщений
│   ├── services/           # Бизнес-логика
│   ├── models/             # Модели данных бота
│   └── utils/              # Утилиты
├── web/                    # FastAPI веб-сервер
│   ├── api/                # API роуты
│   ├── templates/          # HTML шаблоны
│   ├── static/             # CSS, JS, изображения
│   └── services/           # Сервисы веб-части
├── database/               # Модели БД, миграции
│   ├── models/             # SQLAlchemy модели
│   └── migrations/         # Alembic миграции
├── shared/                 # Общий код
│   ├── config/             # Конфигурация
│   └── utils/              # Общие утилиты
├── docker/                 # Docker файлы
├── config.ini              # Конфигурация приложения
└── requirements.txt        # Зависимости Python
```

## Установка и запуск

### 1. Клонирование и настройка

```bash
git clone <repository>
cd random-contest-bot
```

### 2. Настройка конфигурации

Отредактируйте `config.ini` и укажите:
- Токен бота от @BotFather
- ID администратора
- Настройки ngrok (токен и домен)

**Важно**: В Docker окружении `DB_HOST=postgres` и `REDIS_HOST=redis` уже настроены правильно.

### 3. Запуск через Docker (рекомендуется)

```bash
# Сборка и запуск всех контейнеров
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Просмотр логов конкретного сервиса
docker-compose logs -f bot
docker-compose logs -f web
docker-compose logs -f ngrok

# Остановка
docker-compose down

# Пересборка после изменений
docker-compose up -d --build
```

Все сервисы запускаются автоматически:
- **postgres** - База данных PostgreSQL
- **redis** - Redis для кеширования
- **bot** - Telegram бот
- **web** - FastAPI веб-сервер
- **ngrok** - Туннель для вебаппов

Миграции БД применяются автоматически при первом запуске.

### 4. Запуск локально (без Docker)

```bash
# Установка зависимостей
pip install -r requirements.txt

# Настройка БД (измените DB_HOST и REDIS_HOST на localhost в config.ini)
alembic upgrade head

# Запуск бота и веб-сервера
python -m bot.main
python -m web.main
```

## Доступ к сервисам

После запуска через Docker:

- **Веб-сервер**: http://localhost:8000
- **Ngrok веб-интерфейс**: http://localhost:4040
- **Вебаппы через ngrok**: https://gnat-desired-kingfish.ngrok-free.app
- **Админ-панель**: https://gnat-desired-kingfish.ngrok-free.app/admin

## Функционал

### Для пользователей:
- Регистрация в конкурсе через вебапп
- Проверка подписки на канал и спонсоров
- Получение уникального номера участника
- Просмотр результатов конкурса с анимацией

### Для администратора:
- Создание и управление конкурсами
- Управление каналами
- Настройка призовых мест
- Выбор метода розыгрыша (рандом/по активности)
- Просмотр статистики и аналитики
- Публикация результатов в канал

## Лицензия

MIT

