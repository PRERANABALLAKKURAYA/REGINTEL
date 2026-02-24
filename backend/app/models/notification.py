from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Notification(Base):
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"))
    update_id = Column(Integer, ForeignKey("update.id"))
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User")
    update = relationship("Update")
