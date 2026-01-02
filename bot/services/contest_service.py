"""
Сервис для работы с конкурсами
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from database.models import Contest, Participant, Channel, Prize, Sponsor
from database.models.contest import ContestStatus, ContestDrawMethod


class ContestService:
    """Сервис для работы с конкурсами"""
    
    def __init__(self, db: AsyncSession):
        """
        Инициализация сервиса
        
        @param db сессия базы данных
        """
        self.db = db
    
    async def create_contest(
        self,
        title: str,
        channel_id: int,
        end_date: datetime,
        prize_count: int,
        draw_method: ContestDrawMethod = ContestDrawMethod.RANDOM,
        description: Optional[str] = None,
        youtube_channel_id: Optional[str] = None,
        youtube_subscription_days_required: int = 0,
        image_path: Optional[str] = None
    ) -> Contest:
        """
        Создать новый конкурс
        
        @param title название конкурса
        @param channel_id ID канала
        @param end_date дата окончания конкурса
        @param prize_count количество призовых мест
        @param draw_method метод розыгрыша
        @param description описание конкурса
        @param youtube_channel_id ID YouTube канала для обязательной подписки
        @param youtube_subscription_days_required минимальное количество дней подписки
        @param image_path путь к изображению конкурса
        @return созданный конкурс
        """
        contest = Contest(
            title=title,
            channel_id=channel_id,
            end_date=end_date,
            prize_count=prize_count,
            draw_method=draw_method,
            description=description,
            youtube_channel_id=youtube_channel_id,
            youtube_subscription_days_required=youtube_subscription_days_required,
            image_path=image_path,
            status=ContestStatus.DRAFT
        )
        self.db.add(contest)
        await self.db.commit()
        await self.db.refresh(contest)
        return contest
    
    async def get_contest_by_id(self, contest_id: int) -> Optional[Contest]:
        """
        Получить конкурс по ID
        
        @param contest_id ID конкурса
        @return конкурс или None
        """
        result = await self.db.execute(
            select(Contest)
            .options(
                selectinload(Contest.prizes),
                selectinload(Contest.participants),
                selectinload(Contest.sponsors),
                selectinload(Contest.channel)
            )
            .where(Contest.id == contest_id)
        )
        return result.scalar_one_or_none()
    
    async def get_active_contests(self, channel_id: Optional[int] = None) -> List[Contest]:
        """
        Получить активные конкурсы
        
        @param channel_id ID канала (опционально)
        @return список активных конкурсов
        """
        query = select(Contest).where(Contest.status == ContestStatus.ACTIVE)
        if channel_id:
            query = query.where(Contest.channel_id == channel_id)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def publish_contest(self, contest_id: int, message_id: int) -> bool:
        """
        Опубликовать конкурс в канале
        
        @param contest_id ID конкурса
        @param message_id ID сообщения в канале
        @return True если успешно
        """
        contest = await self.get_contest_by_id(contest_id)
        if not contest:
            return False
        
        contest.status = ContestStatus.ACTIVE
        contest.message_id = message_id
        await self.db.commit()
        
        # Планируем автоматическое подведение итогов через Redis
        from shared.services.redis_service import schedule_contest_finish
        await schedule_contest_finish(contest_id, contest.end_date)
        
        return True
    
    async def finish_contest(self, contest_id: int) -> bool:
        """
        Завершить конкурс
        
        @param contest_id ID конкурса
        @return True если успешно
        """
        contest = await self.get_contest_by_id(contest_id)
        if not contest:
            return False
        
        contest.status = ContestStatus.FINISHED
        await self.db.commit()
        return True
    
    async def publish_results(self, contest_id: int, results_message_id: int) -> bool:
        """
        Опубликовать результаты конкурса
        
        @param contest_id ID конкурса
        @param results_message_id ID сообщения с результатами
        @return True если успешно
        """
        contest = await self.get_contest_by_id(contest_id)
        if not contest:
            return False
        
        contest.status = ContestStatus.RESULTS_PUBLISHED
        contest.results_message_id = results_message_id
        await self.db.commit()
        return True
    
    async def get_participants_count(self, contest_id: int) -> int:
        """
        Получить количество участников конкурса
        
        @param contest_id ID конкурса
        @return количество участников
        """
        result = await self.db.execute(
            select(func.count(Participant.id))
            .where(Participant.contest_id == contest_id)
        )
        return result.scalar() or 0
    
    async def get_contest_by_message_id(self, message_id: int) -> Optional[Contest]:
        """
        Получить конкурс по ID сообщения
        
        @param message_id ID сообщения
        @return конкурс или None
        """
        result = await self.db.execute(
            select(Contest).where(Contest.message_id == message_id)
        )
        return result.scalar_one_or_none()

    async def delete_contest(self, contest_id: int) -> bool:
        """
        Удалить конкурс
        
        @param contest_id ID конкурса
        @return True если успешно
        """
        contest = await self.get_contest_by_id(contest_id)
        if not contest:
            return False
            
        await self.db.delete(contest)
        await self.db.commit()
        return True

