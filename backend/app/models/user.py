from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from app.db.base_class import Base

class User(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    subscription_type = Column(String, default="free")
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
