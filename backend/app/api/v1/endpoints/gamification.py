from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.api import deps
from app.models.update import Update

router = APIRouter()


class GamificationResponse(BaseModel):
    points: int
    streak_days: int
    weekly_reads: int
    badges: list[str]


@router.get("/", response_model=GamificationResponse)
def get_gamification(db: Session = Depends(deps.get_db)):
    total_updates = db.query(Update).count()
    points = min(500, total_updates * 12)
    streak_days = 4 if total_updates else 0
    weekly_reads = min(12, total_updates)

    badges = [
        "Regulatory Explorer",
        "Compliance Analyst",
        "Global Strategist",
    ] if total_updates else []

    return {
        "points": points,
        "streak_days": streak_days,
        "weekly_reads": weekly_reads,
        "badges": badges,
    }
