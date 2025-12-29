"""
API роуты для OAuth авторизации через YouTube
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import HTMLResponse
from typing import Optional, Dict
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

router = APIRouter(prefix="/api/youtube", tags=["youtube"])
logger = logging.getLogger(__name__)

# Временные хранилища (в продакшене использовать Redis)
oauth_states: Dict[str, dict] = {}
completed_auths: Dict[int, dict] = {}
user_tokens: Dict[int, dict] = {}

# Константы
STATE_EXPIRATION_MINUTES = 10
AUTH_EXPIRATION_MINUTES = 10
YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']


def cleanup_expired_data():
    """Очистка устаревших данных"""
    current_time = datetime.now()
    expiration_delta = timedelta(minutes=STATE_EXPIRATION_MINUTES)
    
    # Очистка oauth_states
    expired_states = [
        state for state, data in oauth_states.items()
        if current_time - data.get('created_at', current_time) > expiration_delta
    ]
    for state in expired_states:
        oauth_states.pop(state, None)
    
    # Очистка completed_auths
    expired_auths = [
        user_id for user_id, data in completed_auths.items()
        if current_time - data.get('timestamp', current_time) > expiration_delta
    ]
    for user_id in expired_auths:
        completed_auths.pop(user_id, None)


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
        logger.error(f"Token exchange failed: {response.text}")
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


def render_success_page(channel_title: str) -> HTMLResponse:
    """Рендер страницы успешной авторизации"""
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Авторизация успешна</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
                
                body {{
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    background: linear-gradient(135deg, #0a0a0f 0%, #111118 50%, #1a1a24 100%);
                    background-attachment: fixed;
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0;
                    padding: 20px;
                    color: #ffffff;
                }}
                
                .container {{
                    background: rgba(26, 26, 36, 0.95);
                    backdrop-filter: blur(16px);
                    -webkit-backdrop-filter: blur(16px);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 1.25rem;
                    padding: 2.5rem;
                    max-width: 500px;
                    width: 100%;
                    text-align: center;
                    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.6);
                    animation: slideUp 0.6s cubic-bezier(0.4, 0, 0.2, 1);
                }}
                
                @keyframes slideUp {{
                    from {{
                        opacity: 0;
                        transform: translateY(30px);
                    }}
                    to {{
                        opacity: 1;
                        transform: translateY(0);
                    }}
                }}
                
                .icon {{
                    font-size: 5rem;
                    margin-bottom: 1.5rem;
                    animation: scaleInBounce 0.8s cubic-bezier(0.68, -0.55, 0.265, 1.55);
                    display: inline-block;
                    filter: drop-shadow(0 4px 8px rgba(16, 185, 129, 0.3));
                }}
                
                @keyframes scaleInBounce {{
                    0% {{
                        opacity: 0;
                        transform: scale(0.3);
                    }}
                    50% {{
                        transform: scale(1.1);
                    }}
                    100% {{
                        opacity: 1;
                        transform: scale(1);
                    }}
                }}
                
                h1 {{
                    color: #ffffff;
                    margin-bottom: 1rem;
                    font-size: 1.625rem;
                    font-weight: 700;
                    letter-spacing: -0.02em;
                }}
                
                .description {{
                    color: #b0b0c0;
                    margin-bottom: 1.5rem;
                    font-size: 0.9375rem;
                    line-height: 1.6;
                }}
                
                .channel {{
                    background: rgba(16, 185, 129, 0.15);
                    border: 1px solid rgba(16, 185, 129, 0.3);
                    padding: 1rem;
                    border-radius: 0.75rem;
                    margin: 1.5rem 0;
                    font-weight: 600;
                    color: #10b981;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 0.5rem;
                    font-size: 0.9375rem;
                }}
                
                .hint {{
                    color: #707080;
                    font-size: 0.875rem;
                    margin-top: 1.5rem;
                    line-height: 1.5;
                }}
                
                .btn {{
                    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
                    color: white;
                    border: none;
                    padding: 1rem 2rem;
                    border-radius: 0.75rem;
                    font-size: 1rem;
                    font-weight: 600;
                    cursor: pointer;
                    margin-top: 1.5rem;
                    transition: all 300ms cubic-bezier(0.4, 0, 0.2, 1);
                    box-shadow: 0 0 20px rgba(99, 102, 241, 0.25);
                    letter-spacing: 0.01em;
                }}
                
                .btn:hover {{
                    transform: translateY(-2px) scale(1.02);
                    box-shadow: 0 0 30px rgba(99, 102, 241, 0.4), 0 10px 15px -3px rgba(0, 0, 0, 0.6);
                }}
                
                .btn:active {{
                    transform: translateY(0) scale(1);
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="icon">✅</div>
                <h1>Авторизация успешна!</h1>
                <p class="description">Вы успешно авторизовались через YouTube</p>
                <div class="channel">
                    <span>📺</span>
                    <span>{channel_title}</span>
                </div>
                <p class="hint">Вы можете закрыть это окно и вернуться в Telegram</p>
                <button class="btn" id="closeBtn">Закрыть окно</button>
            </div>
            <script>
                (function() {{
                    const closeBtn = document.getElementById('closeBtn');
                    
                    function tryClose() {{
                        // Способ 1: Telegram WebApp API
                        if (window.Telegram && window.Telegram.WebApp) {{
                            try {{
                                window.Telegram.WebApp.close();
                                return true;
                            }} catch(e) {{
                                console.log('Telegram.WebApp.close() failed:', e);
                            }}
                        }}
                        
                        // Способ 2: window.close() для popup окон
                        try {{
                            if (window.opener && !window.opener.closed) {{
                                window.close();
                                return true;
                            }}
                        }} catch(e) {{
                            console.log('window.close() failed:', e);
                        }}
                        
                        return false;
                    }}
                    
                    closeBtn.addEventListener('click', function() {{
                        const closed = tryClose();
                        
                        if (!closed) {{
                            // Если не удалось закрыть, показываем сообщение
                            const hint = document.querySelector('.hint');
                            if (hint) {{
                                hint.innerHTML = 'Пожалуйста, закройте это окно вручную и вернитесь в Telegram.<br>Авторизация уже завершена!';
                                hint.style.color = '#10b981';
                                hint.style.fontWeight = '600';
                            }}
                            closeBtn.textContent = '✓ Готово';
                            closeBtn.style.background = 'linear-gradient(135deg, #10b981 0%, #059669 100%)';
                            closeBtn.disabled = true;
                        }}
                    }});
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
    
    cleanup_expired_data()
    
    try:
        # Генерируем уникальный state для защиты от CSRF
        state = secrets.token_urlsafe(32)
        
        # Сохраняем данные состояния
        oauth_states[state] = {
            'contest_id': contest_id,
            'user_id': user_id,
            'created_at': datetime.now()
        }
        
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
    
    # Проверка state
    if state not in oauth_states:
        logger.error(f"Invalid or expired state: {state[:10]}...")
        return render_error_page(
            "Недействительная сессия",
            "Сессия авторизации истекла или недействительна",
            "Попробуйте начать авторизацию заново"
        )
    
    # Извлекаем данные состояния
    state_data = oauth_states.pop(state)
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
        
        # Сохраняем токены пользователя
        user_tokens[user_id] = {
            'token': access_token,
            'refresh_token': refresh_token,
            'credentials': credentials,
            'timestamp': datetime.now()
        }
        
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
        
        # Сохраняем завершенную авторизацию для polling (временное хранилище)
        completed_auths[user_id] = {
            'channel_id': channel_id,
            'channel_title': channel_title,
            'contest_id': contest_id,
            'timestamp': datetime.now()
        }
        
        logger.info(f"OAuth completed successfully for user {user_id}")
        
        return render_success_page(channel_title)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during token exchange: {e}", exc_info=True)
        return render_error_page(
            "Ошибка авторизации",
            "Произошла ошибка при обмене кода на токен",
            str(e)
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
    cleanup_expired_data()
    
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
    
    # Если в БД нет, проверяем временное хранилище
    if user_id in completed_auths:
        auth_data = completed_auths[user_id]
        
        # Проверяем соответствие contest_id
        if auth_data.get('contest_id') == contest_id:
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
    
    # Если в БД нет, проверяем временное хранилище
    if user_id in user_tokens:
        return user_tokens[user_id].get('credentials')
    
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
