from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, func, Boolean
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Update(Base):
    id = Column(Integer, primary_key=True, index=True)
    authority_id = Column(Integer, ForeignKey("authority.id"))
    title = Column(String, index=True, nullable=False)
    category = Column(String, index=True)
    published_date = Column(DateTime, nullable=False)
    source_link = Column(String, unique=True, nullable=False)
    pdf_file_path = Column(String, nullable=True)  # Path to stored PDF file
    full_text = Column(Text, nullable=True)
    short_summary = Column(Text, nullable=True)
    detailed_summary = Column(Text, nullable=True)
    is_guideline = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    # Embedding vector for RAG (using pgvector later, stored as array/blob for now if needed or ignored)
    # embedding_vector = Column(Vector(1536)) 

    authority = relationship("Authority")
