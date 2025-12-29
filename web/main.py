"""
Главный файл для запуска FastAPI веб-сервера
"""
import uvicorn
import logging
from typing import Optional, Dict
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from shared.config import config
from shared.utils.ngrok import setup_ngrok
from web.api import contests, admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Contest Bot WebApp")

# Подключение статических файлов и шаблонов
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# Подключение папки uploads для доступа к загруженным изображениям
uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# Подключение API роутеров
app.include_router(contests.router)
app.include_router(admin.router)

# Импортируем publish router
from web.api import publish
app.include_router(publish.router)

# Импортируем YouTube auth router
from web.api import youtube_auth
app.include_router(youtube_auth.router)


@app.get("/")
async def root():
    """Корневой роут"""
    return {"message": "Contest Bot WebApp"}


@app.get("/health")
async def health():
    """Проверка здоровья сервиса"""
    return {"status": "ok"}


def check_telegram_webapp_access(request: Request) -> Optional[Dict]:
    """
    Проверить доступ через Telegram WebApp
    
    @param request HTTP запрос
    @return данные авторизации или None
    """
    from web.services.telegram_auth import verify_telegram_webapp_initdata
    
    # Получаем initData из query параметров или заголовков
    init_data = request.query_params.get("_auth") or request.headers.get("X-Telegram-Init-Data")
    
    logger.debug(f"Проверка доступа: initData присутствует: {bool(init_data)}")
    
    if not init_data:
        logger.warning("initData не найден в запросе")
        return None
    
    # Проверяем авторизацию
    auth_data = verify_telegram_webapp_initdata(init_data)
    if not auth_data:
        logger.warning("Проверка initData не прошла")
    else:
        logger.info(f"Авторизация успешна для пользователя: {auth_data.get('user', {}).get('id')}")
    
    return auth_data


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """
    Страница регистрации в конкурсе
    Доступна только через Telegram WebApp
    """
    # Разрешаем загрузку HTML, проверка будет на клиенте
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/results", response_class=HTMLResponse)
async def results_page(request: Request):
    """
    Страница результатов конкурса
    Доступна только через Telegram WebApp
    """
    # Разрешаем загрузку HTML, проверка будет на клиенте
    return templates.TemplateResponse("results.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """
    Страница админ-панели
    Доступна только через Telegram WebApp с валидной авторизацией
    """
    # Разрешаем загрузку HTML, проверка будет на клиенте
    # Это необходимо, так как JavaScript должен успеть получить initData из Telegram WebApp API
    return templates.TemplateResponse("admin.html", {"request": request})


if __name__ == "__main__":
    # Ngrok запускается в отдельном контейнере, поэтому не настраиваем его здесь
    # В Docker окружении ngrok будет работать через отдельный сервис
    uvicorn.run(
        "web.main:app",
        host=config.web_host,
        port=config.web_port,
        reload=False  # Отключаем reload в Docker
    )

