"""
Модель конкурса
"""
from sqlalchemy import Column, String, DateTime, Integer, BigInteger, ForeignKey, Enum, Text, Boolean
from sqlalchemy.orm import relationship
import enum
from .base import BaseModel


class ContestStatus(enum.Enum):
    """Статус конкурса"""
    DRAFT = "draft"  # Черновик
    ACTIVE = "active"  # Активный
    FINISHED = "finished"  # Завершен
    RESULTS_PUBLISHED = "results_published"  # Результаты опубликованы


class ContestDrawMethod(enum.Enum):
    """Метод розыгрыша"""
    RANDOM = "random"  # Случайный выбор
    BY_ACTIVITY = "by_activity"  # По активности


class Contest(BaseModel):
    """Модель конкурса"""
    
    __tablename__ = 'contests'
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    channel_id = Column(BigInteger, ForeignKey('channels.channel_id'), nullable=False, index=True)
    message_id = Column(BigInteger, nullable=True)  # ID сообщения в канале
    results_message_id = Column(BigInteger, nullable=True)  # ID сообщения с результатами
    end_date = Column(DateTime, nullable=False)
    status = Column(Enum(ContestStatus), default=ContestStatus.DRAFT, nullable=False, index=True)
    draw_method = Column(Enum(ContestDrawMethod), default=ContestDrawMethod.RANDOM, nullable=False)
    prize_count = Column(Integer, nullable=False)  # Количество призовых мест
    youtube_channel_id = Column(String(255), nullable=True)  # ID YouTube канала для обязательной подписки
    youtube_subscription_days_required = Column(Integer, default=0, nullable=False)  # Минимальное количество дней подписки
    image_path = Column(String(500), nullable=True)  # Путь к изображению конкурса
    post_to_sponsors = Column(Boolean, default=False, nullable=False)
    
    # Связи
    channel = relationship("Channel", backref="contests")
    prizes = relationship("Prize", back_populates="contest", cascade="all, delete-orphan")
    participants = relationship("Participant", back_populates="contest", cascade="all, delete-orphan")
    sponsors = relationship("Sponsor", back_populates="contest", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Contest(id={self.id}, title={self.title}, status={self.status.value})>"
