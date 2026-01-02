"""
Сервис для работы с участниками конкурсов
"""
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from database.models import Participant, Contest


class ParticipantService:
    """Сервис для работы с участниками"""
    
    def __init__(self, db: AsyncSession):
        """
        Инициализация сервиса
        
        @param db сессия базы данных
        """
        self.db = db
    
    async def register_participant(
        self,
        contest_id: int,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> Optional[Participant]:
        """
        Зарегистрировать участника в конкурсе
        
        @param contest_id ID конкурса
        @param user_id ID пользователя
        @param username username пользователя
        @return зарегистрированный участник или None если уже зарегистрирован
        """
        # Проверяем, не зарегистрирован ли уже
        existing = await self.get_participant(contest_id, user_id)
        if existing:
            return None
        
        # Получаем следующий номер регистрации
        registration_number = await self.get_next_registration_number(contest_id)
        
        participant = Participant(
            contest_id=contest_id,
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            registration_number=registration_number,
            registered_at=datetime.utcnow()
        )
        
        self.db.add(participant)
        await self.db.commit()
        await self.db.refresh(participant)
        return participant
    
    async def get_participant(self, contest_id: int, user_id: int) -> Optional[Participant]:
        """
        Получить участника конкурса
        
        @param contest_id ID конкурса
        @param user_id ID пользователя
        @return участник или None
        """
        result = await self.db.execute(
            select(Participant)
            .where(Participant.contest_id == contest_id)
            .where(Participant.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_next_registration_number(self, contest_id: int) -> int:
        """
        Получить следующий номер регистрации для конкурса
        
        @param contest_id ID конкурса
        @return следующий номер регистрации
        """
        result = await self.db.execute(
            select(func.max(Participant.registration_number))
            .where(Participant.contest_id == contest_id)
        )
        max_number = result.scalar()
        return (max_number or 0) + 1
    
    async def get_all_participants(self, contest_id: int) -> list[Participant]:
        """
        Получить всех участников конкурса
        
        @param contest_id ID конкурса
        @return список участников
        """
        result = await self.db.execute(
            select(Participant)
            .where(Participant.contest_id == contest_id)
            .order_by(Participant.registration_number)
        )
        return list(result.scalars().all())

