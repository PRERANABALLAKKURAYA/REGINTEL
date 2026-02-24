from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from app.db.base_class import Base

class SavedUpdate(Base):
    __tablename__ = "saved_updates"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), index=True)
    update_id = Column(Integer, ForeignKey("update.id"), index=True)
    saved_at = Column(DateTime, server_default=func.now())

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), index=True)
    update_id = Column(Integer, ForeignKey("update.id"), index=True)
    alert_type = Column(String, default="email")  # email, push, in-app
    created_at = Column(DateTime, server_default=func.now())
