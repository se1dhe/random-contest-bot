"""
WebSocket роуты для реалтайм обновлений
"""
import asyncio
import json
import logging
from typing import List, Dict, Set, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from shared.services.redis_service import get_redis

router = APIRouter(prefix="/api/ws", tags=["websocket"])
logger = logging.getLogger(__name__)

class ConnectionManager:
    """Управление WebSocket соединениями"""
    def __init__(self):
        # contest_id -> set(WebSocket)
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        self._redis_listener_task: Optional[asyncio.Task] = None

    async def connect(self, websocket: WebSocket, contest_id: int):
        await websocket.accept()
        if contest_id not in self.active_connections:
            self.active_connections[contest_id] = set()
        self.active_connections[contest_id].add(websocket)
        logger.info(f"Новое подключение к конкурсу {contest_id}. Всего: {len(self.active_connections[contest_id])}")

    def disconnect(self, websocket: WebSocket, contest_id: int):
        if contest_id in self.active_connections:
            self.active_connections[contest_id].remove(websocket)
            if not self.active_connections[contest_id]:
                del self.active_connections[contest_id]
        logger.info(f"Отключение от конкурса {contest_id}")

    async def broadcast_to_contest(self, contest_id: int, message: dict):
        """Отправить сообщение всем подписчикам конкретного конкурса"""
        if contest_id not in self.active_connections:
            return

        dead_connections = set()
        for connection in self.active_connections[contest_id]:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.add(connection)
        
        for dead in dead_connections:
            self.disconnect(dead, contest_id)

manager = ConnectionManager()

async def redis_broadcast_listener():
    """Слушатель Redis для рассылки всем WebSocket клиентам"""
    logger.info("Запуск слушателя Redis для WebSocket рассылки")
    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe("contest_updates")
    
    try:
        while True:
            try:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message['type'] == 'message':
                    data = json.loads(message['data'])
                    contest_id = data.get('contest_id')
                    if contest_id:
                        logger.info(f"Redis broadcast received for contest {contest_id}: {data.get('type')}")
                        await manager.broadcast_to_contest(contest_id, data)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Ошибка в слушателе Redis WS: {e}")
                await asyncio.sleep(1)
    finally:
        await pubsub.unsubscribe("contest_updates")
        await pubsub.close()

@router.websocket("/{contest_id}")
async def websocket_endpoint(websocket: WebSocket, contest_id: int):
    """Эндпоинт для подключения к обновлениям конкурса (публичный)"""
    await manager.connect(websocket, contest_id)
    
    # Запускаем фоновый слушатель Redis, если он еще не запущен
    if not hasattr(manager, '_redis_listener_task') or manager._redis_listener_task is None or manager._redis_listener_task.done():
        manager._redis_listener_task = asyncio.create_task(redis_broadcast_listener())
        
    try:
        while True:
            # Держим соединение открытым. Можно принимать сообщения от клиента если нужно.
            data = await websocket.receive_text()
            # На данный момент мы только рассылаем, поэтому игнорируем входящие данные
    except WebSocketDisconnect:
        manager.disconnect(websocket, contest_id)
    except Exception as e:
        logger.error(f"WS Error: {e}")
        manager.disconnect(websocket, contest_id)
