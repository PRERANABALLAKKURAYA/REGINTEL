from sqlalchemy import Column, Integer, String
from app.db.base_class import Base

class Authority(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    country = Column(String, index=True, nullable=False)
    website_url = Column(String, nullable=False)
