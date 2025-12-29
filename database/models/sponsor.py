"""
Модель спонсора (канала-спонсора)
"""
from sqlalchemy import Column, BigInteger, Integer, ForeignKey, String
from sqlalchemy.orm import relationship
from .base import BaseModel


class Sponsor(BaseModel):
    """Модель спонсора конкурса"""
    
    __tablename__ = 'sponsors'
    
    contest_id = Column(Integer, ForeignKey('contests.id'), nullable=False, index=True)
    channel_id = Column(BigInteger, nullable=False, index=True)
    channel_username = Column(String(255), nullable=True)
    channel_title = Column(String(255), nullable=False)
    
    # Связи
    contest = relationship("Contest", back_populates="sponsors")
    
    def __repr__(self):
        return f"<Sponsor(id={self.id}, contest_id={self.contest_id}, channel_id={self.channel_id})>"

