"""
Модель приза
"""
from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base import BaseModel


class Prize(BaseModel):
    """Модель приза"""
    
    __tablename__ = 'prizes'
    
    contest_id = Column(Integer, ForeignKey('contests.id'), nullable=False, index=True)
    place = Column(Integer, nullable=False)  # Место (1, 2, 3, ...)
    title = Column(String(255), nullable=False)  # Название приза
    description = Column(Text, nullable=True)  # Описание приза
    winner_user_id = Column(BigInteger, nullable=True)  # ID победителя (заполняется после розыгрыша)
    winner_username = Column(String(255), nullable=True)  # Username победителя
    
    # Связи
    contest = relationship("Contest", back_populates="prizes")
    
    def __repr__(self):
        return f"<Prize(id={self.id}, contest_id={self.contest_id}, place={self.place}, title={self.title})>"

