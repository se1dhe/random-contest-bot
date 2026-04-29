"""
API роуты для OAuth авторизации через YouTube
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import HTMLResponse
from typing import Optional
import secrets
import logging
import httpx
import json
from urllib.parse import urlencode
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from shared.config import config
from database.db import get_db
from database.models import YouTubeCredentials
from shared.services.redis_service import (
    store_oauth_state,
    consume_oauth_state,
    store_completed_oauth_auth,
    get_completed_oauth_auth,
)

router = APIRouter(prefix="/api/youtube", tags=["youtube"])
logger = logging.getLogger(__name__)

# Константы
STATE_EXPIRATION_MINUTES = 10
YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']


def get_redirect_uri() -> str:
    """Получить redirect URI для OAuth"""
    base_url = config.webapp_url.rstrip('/')
    return f"{base_url}/api/youtube/callback"


def generate_oauth_url(state: str) -> str:
    """Сгенерировать URL для OAuth авторизации"""
    params = {
        'client_id': config.youtube_client_id,
        'redirect_uri': get_redirect_uri(),
        'response_type': 'code',
        'scope': ' '.join(YOUTUBE_SCOPES),
        'access_type': 'offline',
        'prompt': 'consent',
        'state': state
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict:
    """Обменять код авторизации на токены"""
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        'code': code,
        'client_id': config.youtube_client_id,
        'client_secret': config.youtube_client_secret,
        'redirect_uri': get_redirect_uri(),
        'grant_type': 'authorization_code'
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, data=token_data)
    
    if response.status_code != 200:
        logger.error("YouTube token exchange failed: status=%s body=%s", response.status_code, response.text[:500])
        raise HTTPException(
            status_code=500,
            detail=f"Failed to exchange code for token: {response.text}"
        )
    
    return response.json()


async def get_youtube_channel_info(credentials: Credentials) -> Optional[dict]:
    """Получить информацию о YouTube канале пользователя"""
    try:
        youtube = build('youtube', 'v3', credentials=credentials)
        
        request = youtube.channels().list(part='id,snippet', mine=True)
        response = request.execute()
        
        if 'items' in response and response['items']:
            channel = response['items'][0]
            return {
                'id': channel['id'],
                'title': channel['snippet'].get('title', 'Unknown'),
                'description': channel['snippet'].get('description', '')
            }
        
        return None
        
    except Exception as e:
        logger.error(f"Error fetching channel info: {e}", exc_info=True)
        return None


def create_credentials(token_data: dict) -> Credentials:
    """Создать объект Credentials из данных токена"""
    return Credentials(
        token=token_data.get('access_token'),
        refresh_token=token_data.get('refresh_token'),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config.youtube_client_id,
        client_secret=config.youtube_client_secret,
        scopes=YOUTUBE_SCOPES
    )


def render_error_page(title: str, message: str, details: str = "") -> HTMLResponse:
    """Рендер страницы ошибки"""
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0;
                    padding: 20px;
                }}
                .container {{
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    max-width: 500px;
                    text-align: center;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }}
                .icon {{ font-size: 80px; margin-bottom: 20px; }}
                h1 {{ color: #e53e3e; margin-bottom: 15px; font-size: 24px; }}
                p {{ color: #4a5568; margin-bottom: 10px; }}
                .details {{ color: #718096; font-size: 14px; }}
                .btn {{
                    background: #667eea;
                    color: white;
                    border: none;
                    padding: 15px 30px;
                    border-radius: 10px;
                    font-size: 16px;
                    cursor: pointer;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">❌</div>
                <h1>{title}</h1>
                <p>{message}</p>
                {f'<p class="details">{details}</p>' if details else ''}
                <button class="btn" onclick="window.close()">Закрыть окно</button>
            </div>
        </body>
        </html>
        """,
        status_code=400
    )


def render_success_page_with_redirect(channel_title: str, redirect_url: str, contest_id: int) -> HTMLResponse:
    """
    Рендерить страницу успеха с автоматическим редиректом обратно на страницу регистрации
    
    @param channel_title название YouTube канала
    @param redirect_url URL для редиректа
    @param contest_id ID конкурса
    @return HTMLResponse
    """
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Авторизация успешна</title>
            <script src="https://telegram.org/js/telegram-web-app.js"></script>
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                    color: #fff;
                }}
                .container {{
                    text-align: center;
                    padding: 2rem;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 1rem;
                    backdrop-filter: blur(10px);
                    max-width: 400px;
                }}
                .success-icon {{
                    font-size: 4rem;
                    margin-bottom: 1rem;
                }}
                h1 {{
                    margin: 0 0 1rem 0;
                    font-size: 1.5rem;
                }}
                p {{
                    margin: 0.5rem 0;
                    opacity: 0.9;
                }}
                .channel-name {{
                    font-weight: bold;
                    font-size: 1.2rem;
                    margin: 1rem 0;
                }}
                .loading {{
                    margin-top: 1.5rem;
                    font-size: 0.9rem;
                    opacity: 0.8;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">✅</div>
                <h1>Авторизация успешна!</h1>
                <p>Ваш YouTube канал подключен:</p>
                <p class="channel-name">{channel_title}</p>
                <p class="loading">Возвращаемся на страницу регистрации...</p>
            </div>
            <script>
                (function() {{
                    // Проверяем, открыто ли в Telegram WebApp
                    if (typeof Telegram !== 'undefined' && Telegram.WebApp) {{
                        const tg = Telegram.WebApp;
                        tg.ready();
                        tg.expand();
                        
                        // Пытаемся закрыть окно и обновить родительскую страницу
                        // Если это не работает, делаем редирект
                        setTimeout(function() {{
                            try {{
                                // Пытаемся закрыть WebApp (если открыт в отдельном окне)
                                if (tg.close) {{
                                    tg.close();
                                }}
                            }} catch (e) {{
                                console.log('Не удалось закрыть WebApp, делаем редирект');
                            }}
                            
                            // Редирект на страницу регистрации
                            window.location.href = '{redirect_url}';
                        }}, 1500);
                    }} else {{
                        // Если не в Telegram, просто редиректим
                        setTimeout(function() {{
                            window.location.href = '{redirect_url}';
                        }}, 1500);
                    }}
                }})();
            </script>
        </body>
        </html>
        """
    )


@router.get("/auth")
async def youtube_auth(
    contest_id: int = Query(..., description="ID конкурса"),
    user_id: int = Query(..., description="ID пользователя Telegram"),
    _auth: Optional[str] = Query(None, alias="_auth", description="Telegram initData")
):
    """
    Инициировать OAuth авторизацию через YouTube.
    Перенаправляет пользователя на страницу авторизации Google.
    """
    if not config.youtube_client_id or not config.youtube_client_secret:
        raise HTTPException(
            status_code=500,
            detail="YouTube OAuth не настроен на сервере"
        )
    
    try:
        # Генерируем уникальный state для защиты от CSRF
        state = secrets.token_urlsafe(32)

        await store_oauth_state(
            state=state,
            contest_id=contest_id,
            user_id=user_id,
            ttl_seconds=STATE_EXPIRATION_MINUTES * 60,
        )
        
        # Генерируем URL авторизации
        authorization_url = generate_oauth_url(state)
        
        logger.info(
            f"OAuth initiated - User: {user_id}, Contest: {contest_id}, State: {state[:10]}..."
        )
        
        # Перенаправляем на Google OAuth
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=authorization_url, status_code=302)
        
    except Exception as e:
        logger.error(f"Error initiating OAuth: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Не удалось инициировать OAuth: {str(e)}"
        )


@router.get("/callback")
async def youtube_callback(
    code: Optional[str] = Query(None, description="Код авторизации от Google"),
    state: Optional[str] = Query(None, description="State для проверки CSRF"),
    error: Optional[str] = Query(None, description="Ошибка от Google"),
    db: AsyncSession = Depends(get_db)
):
    """
    Callback endpoint для завершения OAuth авторизации.
    Получает код от Google, обменивает его на токены и сохраняет результат.
    """
    logger.info(f"OAuth callback received - Code: {bool(code)}, State: {bool(state)}, Error: {error}")
    
    # Обработка ошибки от Google
    if error:
        logger.error(f"OAuth error from Google: {error}")
        return render_error_page(
            "Ошибка авторизации",
            "Google вернул ошибку при авторизации",
            error
        )
    
    # Проверка обязательных параметров
    if not code or not state:
        logger.error("Missing required parameters")
        return render_error_page(
            "Неверные параметры",
            "Отсутствуют необходимые параметры авторизации",
            "Попробуйте начать авторизацию заново"
        )
    
    state_data = await consume_oauth_state(state)
    if not state_data:
        logger.error(f"Invalid or expired state: {state[:10]}...")
        return render_error_page(
            "Недействительная сессия",
            "Сессия авторизации истекла или недействительна",
            "Попробуйте начать авторизацию заново"
        )

    contest_id = state_data['contest_id']
    user_id = state_data['user_id']
    
    logger.info(f"State validated - User: {user_id}, Contest: {contest_id}")
    
    try:
        # Обмениваем код на токены
        token_response = await exchange_code_for_token(code)
        
        access_token = token_response.get('access_token')
        refresh_token = token_response.get('refresh_token')
        
        if not access_token:
            raise HTTPException(status_code=500, detail="Access token not received")
        
        logger.info(f"Access token received for user: {user_id}")
        
        # Создаем credentials
        credentials = create_credentials(token_response)
        
        # Получаем информацию о канале
        channel_info = await get_youtube_channel_info(credentials)
        
        if not channel_info:
            logger.error("Failed to get channel info")
            return render_error_page(
                "Канал не найден",
                "Не удалось получить информацию о вашем YouTube канале",
                "Убедитесь, что у вас есть YouTube канал"
            )
        
        channel_id = channel_info['id']
        channel_title = channel_info['title']
        
        logger.info(f"Channel info retrieved - {channel_title} ({channel_id})")
        
        # Сохраняем credentials в БД для постоянного хранения
        creds_dict = {
            'token': access_token,
            'refresh_token': refresh_token,
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': config.youtube_client_id,
            'client_secret': config.youtube_client_secret,
            'scopes': YOUTUBE_SCOPES
        }
        
        # Вычисляем время истечения токена (если указано в ответе)
        expires_at = None
        if 'expires_in' in token_response:
            expires_at = datetime.now() + timedelta(seconds=token_response['expires_in'])
        
        # Проверяем, есть ли уже credentials для этого пользователя
        result = await db.execute(
            select(YouTubeCredentials).where(YouTubeCredentials.user_id == user_id)
        )
        existing_creds = result.scalar_one_or_none()
        
        if existing_creds:
            # Обновляем существующие credentials
            existing_creds.youtube_channel_id = channel_id
            existing_creds.token = access_token
            existing_creds.refresh_token = refresh_token
            existing_creds.token_uri = creds_dict['token_uri']
            existing_creds.client_id = creds_dict['client_id']
            existing_creds.client_secret = creds_dict['client_secret']
            existing_creds.scopes = json.dumps(creds_dict['scopes']) if isinstance(creds_dict['scopes'], list) else creds_dict['scopes']
            existing_creds.expires_at = expires_at
            existing_creds.updated_at = datetime.now()
            logger.info(f"Updated YouTube credentials for user {user_id}")
        else:
            # Создаем новые credentials
            new_creds = YouTubeCredentials.from_credentials_dict(
                user_id=user_id,
                youtube_channel_id=channel_id,
                creds_dict=creds_dict,
                expires_at=expires_at
            )
            db.add(new_creds)
            logger.info(f"Saved new YouTube credentials for user {user_id}")
        
        await db.commit()
        
        await store_completed_oauth_auth(
            user_id=user_id,
            contest_id=contest_id,
            channel_id=channel_id,
            channel_title=channel_title,
            ttl_seconds=STATE_EXPIRATION_MINUTES * 60,
        )
        
        logger.info(f"OAuth completed successfully for user {user_id}")
        
        # Получаем информацию о боте для формирования ссылки
        bot_username = None
        try:
            from aiogram import Bot
            bot = Bot(token=config.bot_token)
            bot_info = await bot.get_me()
            bot_username = bot_info.username
            await bot.session.close()
        except Exception as e:
            logger.warning(f"Не удалось получить информацию о боте: {e}")
        
        # Формируем URL для редиректа обратно на страницу регистрации
        if bot_username:
            redirect_url = config.build_mini_app_link(bot_username, f"contest_{contest_id}")
        else:
            # Fallback: используем прямой URL (если startapp не работает)
            redirect_url = f"{config.webapp_url}?tgWebAppData="
        
        return render_success_page_with_redirect(channel_title, redirect_url, contest_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during token exchange: {e}", exc_info=True)
        return render_error_page(
            "Ошибка авторизации",
            "Произошла ошибка при обмене кода на токен",
            str(e)
        )


@router.delete("/disconnect")
async def disconnect_youtube(
    user_id: int = Query(..., description="ID пользователя"),
    db: AsyncSession = Depends(get_db)
):
    """
    Отвязать YouTube аккаунт пользователя
    
    @param user_id ID пользователя Telegram
    @param db сессия БД
    @return результат отвязки
    """
    try:
        result = await db.execute(
            select(YouTubeCredentials).where(YouTubeCredentials.user_id == user_id)
        )
        credentials = result.scalar_one_or_none()
        
        if not credentials:
            raise HTTPException(
                status_code=404,
                detail="YouTube аккаунт не привязан"
            )
        
        # Правильный способ удаления в async SQLAlchemy
        from sqlalchemy import delete
        await db.execute(delete(YouTubeCredentials).where(YouTubeCredentials.user_id == user_id))
        await db.commit()
        
        logger.info(f"YouTube аккаунт отвязан для пользователя {user_id}")
        
        return {"success": True, "message": "YouTube аккаунт успешно отвязан"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка отвязки YouTube аккаунта: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Ошибка при отвязке YouTube аккаунта"
        )


@router.get("/check-auth")
async def check_auth_status(
    user_id: int = Query(..., description="ID пользователя"),
    contest_id: int = Query(..., description="ID конкурса"),
    db: AsyncSession = Depends(get_db)
):
    """
    Проверить статус авторизации пользователя.
    Используется для polling со стороны клиента.
    Сначала проверяет БД, потом временное хранилище.
    """
    # Сначала проверяем БД на наличие сохраненных credentials
    result = await db.execute(
        select(YouTubeCredentials).where(YouTubeCredentials.user_id == user_id)
    )
    db_creds = result.scalar_one_or_none()
    
    if db_creds:
        # Получаем название канала через YouTube API, если оно не сохранено
        channel_title = None
        if db_creds.youtube_channel_id:
            try:
                credentials = db_creds.to_dict()
                creds_obj = create_credentials(credentials)
                channel_info = await get_youtube_channel_info(creds_obj)
                if channel_info:
                    channel_title = channel_info.get('title')
            except Exception as e:
                logger.warning(f"Не удалось получить название канала для user_id={user_id}: {e}")
        
        return {
            'authenticated': True,
            'channel_id': db_creds.youtube_channel_id,
            'channel_title': channel_title
        }
    
    # Если в БД нет, проверяем временное хранилище в Redis
    auth_data = await get_completed_oauth_auth(user_id)
    if auth_data and auth_data.get('contest_id') == contest_id:
        return {
            'authenticated': True,
            'channel_id': auth_data['channel_id'],
            'channel_title': auth_data['channel_title']
        }
    
    return {'authenticated': False}


async def get_user_credentials(user_id: int, db: Optional[AsyncSession] = None) -> Optional[Credentials]:
    """
    Получить сохраненные credentials пользователя.
    Сначала проверяет БД, потом временное хранилище.
    
    Args:
        user_id: ID пользователя Telegram
        db: сессия БД (опционально, если не передана, будет использоваться временное хранилище)
        
    Returns:
        Credentials если найдены, иначе None
    """
    # Сначала проверяем БД
    if db:
        try:
            result = await db.execute(
                select(YouTubeCredentials).where(YouTubeCredentials.user_id == user_id)
            )
            db_creds = result.scalar_one_or_none()
            
            if db_creds:
                creds_dict = db_creds.to_dict()
                return Credentials(**creds_dict)
        except Exception as e:
            logger.error(f"Error getting credentials from DB for user {user_id}: {e}", exc_info=True)
    
    return None


async def check_youtube_subscription(user_id: int, target_channel_id: str, db: Optional[AsyncSession] = None) -> bool:
    """
    Проверить, подписан ли пользователь на указанный YouTube канал.
    
    Args:
        user_id: ID пользователя Telegram
        target_channel_id: ID YouTube канала для проверки
        db: сессия БД (опционально)
        
    Returns:
        True если подписан, False если нет
    """
    credentials = await get_user_credentials(user_id, db)
    if not credentials:
        logger.warning(f"No credentials found for user {user_id}")
        return False
    
    try:
        # Получаем ID канала пользователя из БД
        user_channel_id = None
        if db:
            result = await db.execute(
                select(YouTubeCredentials).where(YouTubeCredentials.user_id == user_id)
            )
            db_creds = result.scalar_one_or_none()
            if db_creds and db_creds.youtube_channel_id:
                user_channel_id = db_creds.youtube_channel_id
        
        # Если пользователь пытается подписаться на свой собственный канал - считаем это успешным
        if user_channel_id and user_channel_id == target_channel_id:
            logger.info(f"User {user_id} owns the target channel {target_channel_id}, subscription check passed")
            return True
        
        youtube = build('youtube', 'v3', credentials=credentials)
        
        # Получаем подписки пользователя
        request = youtube.subscriptions().list(
            part='snippet',
            mine=True,
            maxResults=50
        )
        
        # Проходим по всем страницам результатов
        while request:
            response = request.execute()
            
            for item in response.get('items', []):
                channel_id = item['snippet']['resourceId']['channelId']
                if channel_id == target_channel_id:
                    logger.info(f"Subscription found for user {user_id} to channel {target_channel_id}")
                    return True
            
            request = youtube.subscriptions().list_next(request, response)
        
        logger.info(f"No subscription found for user {user_id} to channel {target_channel_id}")
        return False
        
    except Exception as e:
        logger.error(f"Error checking subscription for user {user_id}: {e}", exc_info=True)
        return False
