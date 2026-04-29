# Скрипты для работы с базой данных

## API Regression Check

Скрипт `api_regression_check.sh` выполняет быстрые регрессионные проверки API:
- доступность web root;
- базовые публичные проверки;
- защита админских и publish-эндпоинтов (403 без auth);
- опционально: авторизованные проверки схемы `paginated`-ответа админ-списка и `republish-diff`.

### Использование

Без авторизации (базовый набор):
```bash
./scripts/api_regression_check.sh
```

С авторизацией admin (`_auth` от Telegram WebApp) и проверкой конкретного конкурса:
```bash
ADMIN_AUTH='<initData>' TEST_CONTEST_ID=123 ./scripts/api_regression_check.sh
```

Опционально можно переопределить базовый URL:
```bash
BASE_URL='http://localhost:8000' ./scripts/api_regression_check.sh
```

## Удаление всех конкурсов

Скрипт `delete_all_contests.py` позволяет удалить все конкурсы из базы данных вместе с связанными данными (призы, участники, спонсоры).

### Использование

**В контейнере:**
```bash
docker-compose exec web python scripts/delete_all_contests.py
```

**Или через run:**
```bash
docker-compose run --rm web python scripts/delete_all_contests.py
```

### Внимание!

⚠️ **Это действие необратимо!** Скрипт удалит:
- Все конкурсы
- Все призы
- Всех участников
- Всех спонсоров

Перед выполнением скрипт запросит подтверждение. Введите `yes` для подтверждения.
