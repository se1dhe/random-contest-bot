"""
Главный файл для запуска FastAPI веб-сервера
"""
import uvicorn
import logging
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from shared.config import config
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


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Корневой роут - SSR подход: сервер определяет состояние и отдает нужный HTML
    При использовании startapp= Telegram открывает WebApp на корневой странице
    """
    # Получаем initData из query параметров (если есть)
    init_data = request.query_params.get("tgWebAppData")
    
    # Если initData есть в query - проверяем и рендерим сразу
    if init_data:
        return await render_webapp_page(request, init_data)
    
    # Если нет - рендерим базовый HTML, который получит initData на клиенте
    return templates.TemplateResponse("webapp_loader.html", {"request": request})


@app.post("/api/webapp/render", response_class=HTMLResponse)
async def render_webapp(request: Request):
    """
    API endpoint для рендеринга WebApp страницы на основе initData
    Клиент отправляет initData, сервер проверяет и возвращает нужный HTML
    """
    try:
        data = await request.json()
        init_data = data.get("initData")
        
        if not init_data:
            return HTMLResponse(
                content='<div style="padding: 2rem; text-align: center; color: #fff;">Ошибка: initData не передан</div>',
                status_code=400
            )
        
        return await render_webapp_page(request, init_data)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка рендеринга WebApp: {e}")
        return HTMLResponse(
            content=f'<div style="padding: 2rem; text-align: center; color: #fff;">Ошибка: {str(e)}</div>',
            status_code=500
        )


async def render_webapp_page(request: Request, init_data: str):
    """
    Рендерить нужную страницу WebApp на основе initData
    
    @param request HTTP запрос
    @param init_data initData от Telegram
    @return HTMLResponse с нужной страницей
    """
    from web.services.telegram_auth import verify_telegram_webapp_initdata
    from database.db import AsyncSessionLocal
    from bot.services.contest_service import ContestService
    from bot.services.participant_service import ParticipantService
    from database.models.contest import ContestStatus
    from urllib.parse import parse_qsl
    import json
    
    # Проверяем подпись initData
    auth_data = verify_telegram_webapp_initdata(init_data)
    if not auth_data:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Неверная подпись Telegram"
        })
    
    user = auth_data.get("user", {})
    user_id = user.get("id")
    
    if not user_id:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Не удалось получить ID пользователя"
        })
    
    # Получаем start_param из initData
    parsed_data = dict(parse_qsl(init_data))
    start_param = parsed_data.get("start_param")
    
    if not start_param:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Не указан параметр конкурса"
        })
    
    # Определяем тип и contest_id
    if start_param.startswith("contest_"):
        contest_id = int(start_param.split("_")[1])
        return await render_contest_page(request, contest_id, user_id, user)
    elif start_param.startswith("results_"):
        contest_id = int(start_param.split("_")[1])
        return await render_results_page(request, contest_id, user_id, user)
    else:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": "Неверный формат параметра"
        })


async def render_contest_page(request: Request, contest_id: int, user_id: int, user: dict):
    """
    Рендерить страницу конкурса (регистрация или уже зарегистрирован)
    
    @param request HTTP запрос
    @param contest_id ID конкурса
    @param user_id ID пользователя
    @param user данные пользователя
    @return HTMLResponse
    """
    from database.db import AsyncSessionLocal
    from bot.services.contest_service import ContestService
    from bot.services.participant_service import ParticipantService
    from database.models.contest import ContestStatus
    from datetime import datetime
    
    async with AsyncSessionLocal() as db:
        contest_service = ContestService(db)
        participant_service = ParticipantService(db)
        
        # Получаем конкурс
        contest = await contest_service.get_contest_by_id(contest_id)
        
        if not contest:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": "Конкурс не найден"
            })
        
        # Проверяем статус конкурса
        if contest.status == ContestStatus.FINISHED or contest.status == ContestStatus.RESULTS_PUBLISHED:
            # Конкурс завершен - показываем результаты
            return await render_results_page(request, contest_id, user_id, user)
        
        if contest.status != ContestStatus.ACTIVE:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": "Конкурс не активен"
            })
        
        # Проверяем, не закончился ли конкурс по дате
        if contest.end_date < datetime.utcnow():
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": "Конкурс уже завершен"
            })
        
        # Проверяем регистрацию
        participant = await participant_service.get_participant(contest_id, user_id)
        
        if participant:
            # Уже зарегистрирован
            return templates.TemplateResponse("already_registered.html", {
                "request": request,
                "contest": contest,
                "participant": participant,
                "user": user
            })
        else:
            # Не зарегистрирован - проверяем YouTube авторизацию
            from web.api.youtube_auth import get_user_credentials
            from web.api.youtube_auth import check_youtube_subscription
            
            youtube_connected = False
            youtube_subscribed = False
            youtube_channel_title = None
            required_youtube_channel_title = None
            required_youtube_channel_url = None
            
            if contest.youtube_channel_id:
                # Получаем название требуемого YouTube канала
                try:
                    # Формируем URL канала
                    channel_id = contest.youtube_channel_id
                    if channel_id.startswith('@'):
                        required_youtube_channel_url = f"https://youtube.com/{channel_id}"
                    elif channel_id.startswith('http'):
                        required_youtube_channel_url = channel_id
                    elif channel_id.startswith('UC') or channel_id.startswith('HC'):
                        required_youtube_channel_url = f"https://youtube.com/channel/{channel_id}"
                    else:
                        required_youtube_channel_url = f"https://youtube.com/@{channel_id}"
                    
                    # Пытаемся получить название канала через API
                    if hasattr(config, 'youtube_api_key') and config.youtube_api_key:
                        try:
                            import httpx
                            async with httpx.AsyncClient() as client:
                                # Получаем channel ID если передан username
                                if channel_id.startswith('@'):
                                    # Получаем channel ID по username
                                    search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={channel_id[1:]}&type=channel&key={config.youtube_api_key}&maxResults=1"
                                    search_response = await client.get(search_url)
                                    if search_response.status_code == 200:
                                        search_data = search_response.json()
                                        if search_data.get('items'):
                                            channel_id = search_data['items'][0]['snippet']['channelId']
                                
                                # Получаем информацию о канале
                                channel_url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet&id={channel_id}&key={config.youtube_api_key}"
                                channel_response = await client.get(channel_url)
                                if channel_response.status_code == 200:
                                    channel_data = channel_response.json()
                                    if channel_data.get('items'):
                                        required_youtube_channel_title = channel_data['items'][0]['snippet']['title']
                        except Exception as e:
                            logger.warning(f"Не удалось получить название YouTube канала {channel_id}: {e}")
                            # Используем ID как название, если не удалось получить
                            required_youtube_channel_title = channel_id
                    else:
                        # Если нет API ключа, используем ID как название
                        required_youtube_channel_title = channel_id
                except Exception as e:
                    logger.warning(f"Ошибка получения информации о YouTube канале: {e}")
                    required_youtube_channel_title = contest.youtube_channel_id
                    required_youtube_channel_url = f"https://youtube.com/channel/{contest.youtube_channel_id}"
                
                credentials = await get_user_credentials(user_id, db)
                if credentials:
                    youtube_connected = True
                    # Проверяем подписку
                    try:
                        youtube_subscribed = await check_youtube_subscription(
                            user_id=user_id,
                            target_channel_id=contest.youtube_channel_id,
                            db=db
                        )
                    except Exception as e:
                        logger.warning(f"Ошибка проверки подписки YouTube: {e}")
                        youtube_subscribed = False
                    
                    # Получаем название канала пользователя
                    from database.models import YouTubeCredentials
                    from sqlalchemy import select
                    result = await db.execute(
                        select(YouTubeCredentials).where(YouTubeCredentials.user_id == user_id)
                    )
                    user_creds = result.scalar_one_or_none()
                    if user_creds and user_creds.youtube_channel_id:
                        # Пытаемся получить название канала через YouTube API
                        try:
                            from web.api.youtube_auth import create_credentials, get_youtube_channel_info
                            credentials_dict = user_creds.to_dict()
                            creds_obj = create_credentials(credentials_dict)
                            channel_info = await get_youtube_channel_info(creds_obj)
                            if channel_info and channel_info.get('title'):
                                youtube_channel_title = channel_info['title']
                            else:
                                # Если не удалось получить название, используем ID
                                youtube_channel_title = user_creds.youtube_channel_id
                        except Exception as e:
                            logger.warning(f"Не удалось получить название YouTube канала пользователя {user_id}: {e}")
                            # Используем ID как fallback
                            youtube_channel_title = user_creds.youtube_channel_id
            
            # Показываем форму регистрации
            return templates.TemplateResponse("register_ssr.html", {
                "request": request,
                "contest": contest,
                "user": user,
                "youtube_connected": youtube_connected,
                "youtube_subscribed": youtube_subscribed,
                "youtube_channel_title": youtube_channel_title,
                "required_youtube_channel_title": required_youtube_channel_title or contest.youtube_channel_id,
                "required_youtube_channel_url": required_youtube_channel_url or f"https://youtube.com/channel/{contest.youtube_channel_id}"
            })


async def render_results_page(request: Request, contest_id: int, user_id: int, user: dict):
    """
    Рендерить страницу результатов конкурса
    
    @param request HTTP запрос
    @param contest_id ID конкурса
    @param user_id ID пользователя
    @param user данные пользователя
    @return HTMLResponse
    """
    from database.db import AsyncSessionLocal
    from bot.services.contest_service import ContestService
    from bot.services.participant_service import ParticipantService
    
    async with AsyncSessionLocal() as db:
        contest_service = ContestService(db)
        participant_service = ParticipantService(db)
        
        # Получаем конкурс
        contest = await contest_service.get_contest_by_id(contest_id)
        
        if not contest:
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error": "Конкурс не найден"
            })
        
        # Проверяем регистрацию
        participant = await participant_service.get_participant(contest_id, user_id)
        
        # Получаем победителей
        winners = []
        user_prize = None
        if contest.prizes:
            for prize in contest.prizes:
                if prize.winner_user_id:
                    winners.append(prize)
                    if prize.winner_user_id == user_id:
                        user_prize = prize
        
        # Определяем, победил ли пользователь
        if user_prize:
            # Победитель
            return templates.TemplateResponse("winner.html", {
                "request": request,
                "contest": contest,
                "prize": user_prize,
                "user": user
            })
        elif participant:
            # Участник, но не победитель
            return templates.TemplateResponse("loser.html", {
                "request": request,
                "contest": contest,
                "user": user
            })
        else:
            # Не участвовал - показываем общие результаты
            return templates.TemplateResponse("results_ssr.html", {
                "request": request,
                "contest": contest,
                "winners": winners,
                "user": user
            })


@app.get("/health")
async def health():
    """Проверка здоровья сервиса"""
    return {"status": "ok"}


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

