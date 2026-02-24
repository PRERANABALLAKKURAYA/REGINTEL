from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Badge(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String)
    icon_url = Column(String)

class UserBadge(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    badge_id = Column(Integer, ForeignKey("badge.id"))
    earned_at = Column(DateTime, server_default=func.now())

    user = relationship("User")
    badge = relationship("Badge")

class UserStats(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), unique=True)
    points = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)
    last_login = Column(DateTime)
    
    user = relationship("User")
