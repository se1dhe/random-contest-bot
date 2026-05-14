"""
Сервис для розыгрыша призов
"""
import secrets
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from database.models import Contest, Participant, Prize
from database.models.contest import ContestDrawMethod


class DrawService:
    """Сервис для розыгрыша призов"""
    
    def __init__(self, db: AsyncSession):
        """
        Инициализация сервиса
        
        @param db сессия базы данных
        """
        self.db = db
    
    async def draw_winners(self, contest_id: int) -> bool:
        """
        Провести розыгрыш призов
        
        @param contest_id ID конкурса
        @return True если розыгрыш успешно проведен
        """
        # Получаем конкурс
        result = await self.db.execute(
            select(Contest)
            .options(
                selectinload(Contest.prizes),
                selectinload(Contest.participants)
            )
            .where(Contest.id == contest_id)
        )
        contest = result.scalar_one_or_none()
        
        if not contest:
            return False

        # Повторный вызов розыгрыша не должен перезаписывать уже назначенных победителей.
        if any(prize.winner_user_id for prize in contest.prizes):
            return True
        
        # Получаем всех участников
        participants = contest.participants
        if len(participants) < len(contest.prizes):
            return False  # Недостаточно участников
        
        # Выбираем победителей в зависимости от метода
        if contest.draw_method == ContestDrawMethod.RANDOM:
            winners = self._draw_random(participants, len(contest.prizes))
        else:  # BY_ACTIVITY
            winners = self._draw_by_activity(participants, len(contest.prizes))
        
        # Назначаем призы
        prizes = sorted(contest.prizes, key=lambda p: p.place)
        for i, prize in enumerate(prizes):
            if i < len(winners):
                winner = winners[i]
                prize.winner_user_id = winner.user_id
                prize.winner_username = winner.username
                prize.winner_firstname = winner.first_name
        
        await self.db.commit()
        return True
    
    def _draw_random(self, participants: List[Participant], count: int) -> List[Participant]:
        """
        Случайный розыгрыш
        
        @param participants список участников
        @param count количество победителей
        @return список победителей
        """
        return secrets.SystemRandom().sample(participants, min(count, len(participants)))
    
    def _draw_by_activity(self, participants: List[Participant], count: int) -> List[Participant]:
        """
        Розыгрыш по активности
        
        @param participants список участников
        @param count количество победителей
        @return список победителей
        """
        # Сортируем по активности (activity_score) по убыванию
        sorted_participants = sorted(
            participants,
            key=lambda p: p.activity_score,
            reverse=True
        )
        return sorted_participants[:count]
    
    async def get_winners(self, contest_id: int) -> List[Prize]:
        """
        Получить список победителей конкурса
        
        @param contest_id ID конкурса
        @return список призов с победителями
        """
        result = await self.db.execute(
            select(Prize)
            .where(Prize.contest_id == contest_id)
            .where(Prize.winner_user_id.isnot(None))
            .order_by(Prize.place)
        )
        return list(result.scalars().all())
