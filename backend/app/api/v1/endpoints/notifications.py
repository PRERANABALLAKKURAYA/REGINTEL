from typing import List
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api import deps
from app.models.update import Update

router = APIRouter()


class NotificationItem(BaseModel):
    id: int
    title: str
    source_link: str
    published_date: str
    is_read: bool
    authority: str


@router.get("/", response_model=List[NotificationItem])
def list_notifications(db: Session = Depends(deps.get_db)):
    updates = db.query(Update).order_by(Update.published_date.desc()).limit(5).all()
    notifications = [
        {
            "id": update.id,
            "title": update.title,
            "source_link": update.source_link,
            "published_date": update.published_date.isoformat(),
            "is_read": False,
            "authority": update.authority.name if update.authority else "Unknown",
        }
        for update in updates
    ]
    return notifications
