from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class AuthorityDetail(BaseModel):
    id: int
    name: str
    country: str
    website_url: str

    class Config:
        from_attributes = True

class UpdateBase(BaseModel):
    title: str
    category: Optional[str] = None
    source_link: str
    published_date: datetime
    pdf_file_path: Optional[str] = None
    full_text: Optional[str] = None
    short_summary: Optional[str] = None
    detailed_summary: Optional[str] = None

class UpdateCreate(UpdateBase):
    authority_id: int

class UpdateUpdate(UpdateBase):
    pass

class Update(UpdateBase):
    id: int
    authority_id: int
    authority: Optional[AuthorityDetail] = None
    created_at: datetime
    pdf_file_path: Optional[str] = None

    class Config:
        from_attributes = True
