"""
Модель действий администратора
"""
from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from .base import BaseModel


class AdminAction(BaseModel):
    """История действий администратора"""

    __tablename__ = 'admin_actions'

    actor_user_id = Column(BigInteger, nullable=False, index=True)
    action_type = Column(String(100), nullable=False, index=True)
    target_type = Column(String(50), nullable=False, index=True)
    target_id = Column(String(255), nullable=True)
    contest_id = Column(Integer, ForeignKey('contests.id', ondelete='SET NULL'), nullable=True, index=True)
    status = Column(String(50), nullable=False, default='success')
    message = Column(Text, nullable=True)
    payload = Column(JSON, nullable=True)

    contest = relationship("Contest")

    def __repr__(self):
        return (
            f"<AdminAction(id={self.id}, actor_user_id={self.actor_user_id}, "
            f"action_type={self.action_type}, target_type={self.target_type}, status={self.status})>"
        )
