from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api import deps
from app.models.user import User
import json

router = APIRouter()


class UserPreferences(BaseModel):
    authorities: list[int] = []
    categories: list[str] = []
    notification_email: bool = True
    notification_push: bool = True


@router.post("/me/preferences")
def set_user_preferences(
    prefs: UserPreferences,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    current_user.preferences = json.dumps(prefs.dict())
    db.add(current_user)
    db.commit()
    return {"message": "Preferences saved", "preferences": prefs}


@router.get("/me/preferences")
def get_user_preferences(current_user: User = Depends(deps.get_current_active_user)):
    if current_user.preferences:
        return json.loads(current_user.preferences)
    return {
        "authorities": [],
        "categories": [],
        "notification_email": True,
        "notification_push": True,
    }
