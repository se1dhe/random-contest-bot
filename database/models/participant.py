"""
Модель участника конкурса
"""
from sqlalchemy import Column, BigInteger, Integer, ForeignKey, DateTime, Index, String
from sqlalchemy.orm import relationship
from .base import BaseModel


class Participant(BaseModel):
    """Модель участника конкурса"""
    
    __tablename__ = 'participants'
    
    contest_id = Column(Integer, ForeignKey('contests.id'), nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    registration_number = Column(Integer, nullable=False)  # Уникальный номер регистрации
    registered_at = Column(DateTime, nullable=False)
    activity_score = Column(Integer, default=0, nullable=False)  # Очки активности (для метода по активности)
    
    # Связи
    contest = relationship("Contest", back_populates="participants")
    
    # Уникальный индекс: один пользователь может зарегистрироваться только один раз на конкурс
    __table_args__ = (
        Index('uq_contest_user', 'contest_id', 'user_id', unique=True),
        Index('uq_participants_contest_registration_number', 'contest_id', 'registration_number', unique=True),
    )
    
    def __repr__(self):
        return f"<Participant(id={self.id}, contest_id={self.contest_id}, user_id={self.user_id}, number={self.registration_number})>"
