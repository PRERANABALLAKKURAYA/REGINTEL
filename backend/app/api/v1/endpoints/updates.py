from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.db.session import SessionLocal
from app.models.update import Update as UpdateModel
from app.models.authority import Authority
from app.models.saved_update import SavedUpdate, Alert
from app.schemas.update import Update, UpdateCreate
from pydantic import BaseModel
import tempfile
from datetime import datetime
import json

router = APIRouter()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/homepage", response_model=List[Update])
def read_homepage_updates(limit: int = 20, db: Session = Depends(get_db)):
    """
    Get balanced updates showing all authorities.
    Returns: balanced mix of recent updates from all 7 authorities (FDA, EMA, ICH, MHRA, PMDA, CDSCO, NMPA).
    """
    # Get list of all authorities
    authorities = db.query(Authority).all()
    all_updates = []
    
    # Get recent updates per authority to ensure diversity
    per_authority = max(1, limit // len(authorities))
    
    for authority in authorities:
        auth_updates = (
            db.query(UpdateModel)
            .options(joinedload(UpdateModel.authority))
            .filter(UpdateModel.authority_id == authority.id)
            .order_by(UpdateModel.published_date.desc())
            .limit(per_authority)
            .all()
        )
        all_updates.extend(auth_updates)
    
    # Sort by published date descending and limit
    all_updates.sort(key=lambda x: x.published_date, reverse=True)
    all_updates = all_updates[:limit]
    
    # Log returned records
    by_authority = {}
    for update in all_updates:
        auth_name = update.authority.name if update.authority else "Unknown"
        by_authority[auth_name] = by_authority.get(auth_name, 0) + 1
    
    print(f"[UPDATES] Homepage returned {len(all_updates)} records")
    print(f"[UPDATES] Distribution: {by_authority}")
    
    return all_updates

@router.get("/", response_model=List[Update])
def read_updates(skip: int = 0, limit: int = 15, authority_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = (
        db.query(UpdateModel)
        .options(joinedload(UpdateModel.authority))
        .order_by(UpdateModel.published_date.desc())
    )
    
    # Filter by authority if provided
    if authority_id is not None:
        query = query.filter(UpdateModel.authority_id == authority_id)
    
    updates = (
        query
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    # Log returned records
    print(f"[UPDATES] Returned {len(updates)} records (limit={limit}, authority_id={authority_id})")
    for update in updates[:10]:
        authority_name = update.authority.name if update.authority else "Unknown"
        print(f"[UPDATES] {authority_name} | {update.published_date} | {update.title[:80]}")
    return updates

@router.post("/", response_model=Update)
def create_update(update: UpdateCreate, db: Session = Depends(get_db)):
    db_update = UpdateModel(**update.dict())
    db.add(db_update)
    db.commit()
    db.refresh(db_update)
    return db_update

@router.get("/{update_id}", response_model=Update)
def read_update(update_id: int, db: Session = Depends(get_db)):
    db_update = db.query(UpdateModel).filter(UpdateModel.id == update_id).first()
    if db_update is None:
        raise HTTPException(status_code=404, detail="Update not found")
    return db_update

class EmailRequest(BaseModel):
    recipient_email: str


class AlertRequest(BaseModel):
    alert_type: str = "email"  # email, push, in-app


@router.post("/{update_id}/email")
def email_summary(update_id: int, request: EmailRequest, db: Session = Depends(get_db)):
    """Email the update summary to the user"""
    db_update = db.query(UpdateModel).filter(UpdateModel.id == update_id).first()
    if db_update is None:
        raise HTTPException(status_code=404, detail="Update not found")
    
    # In production, integrate with SendGrid/AWS SES
    # For now, return mock response
    return {
        "status": "success",
        "message": f"Email sent to {request.recipient_email}",
        "update_id": update_id,
        "title": db_update.title,
        "timestamp": datetime.utcnow(),
    }


@router.post("/{update_id}/export-pdf")
def export_pdf(update_id: int, db: Session = Depends(get_db)):
    """Export the update as PDF"""
    db_update = db.query(UpdateModel).filter(UpdateModel.id == update_id).first()
    if db_update is None:
        raise HTTPException(status_code=404, detail="Update not found")
    
    # Generate simple PDF content
    pdf_content = f"""
REGULATORY UPDATE EXPORT

Title: {db_update.title}
Authority: {db_update.authority.name if db_update.authority else 'Unknown'}
Date: {db_update.published_date.strftime('%Y-%m-%d')}
Category: {db_update.category}

Summary:
{db_update.short_summary or 'N/A'}

Full Text:
{db_update.full_text or 'N/A'}

Source: {db_update.source_link}
    """.strip()
    
    # Return as plain text for now (can integrate reportlab for proper PDF)
    return {
        "status": "success",
        "message": "PDF export prepared",
        "update_id": update_id,
        "content": pdf_content,
        "filename": f"update_{update_id}_{datetime.utcnow().strftime('%Y%m%d')}.txt",
    }


@router.post("/{update_id}/save")
def save_update(update_id: int, db: Session = Depends(get_db)):
    """Save an update for later reading"""
    db_update = db.query(UpdateModel).filter(UpdateModel.id == update_id).first()
    if db_update is None:
        raise HTTPException(status_code=404, detail="Update not found")
    
    # For now, return mock response (in production, save to DB with user_id)
    return {
        "status": "success",
        "message": "Update saved for later",
        "update_id": update_id,
        "title": db_update.title,
        "saved_at": datetime.utcnow(),
    }


@router.post("/{update_id}/alert")
def set_alert(update_id: int, request: AlertRequest, db: Session = Depends(get_db)):
    """Set an alert for this update"""
    db_update = db.query(UpdateModel).filter(UpdateModel.id == update_id).first()
    if db_update is None:
        raise HTTPException(status_code=404, detail="Update not found")
    
    # For now, return mock response (in production, save Alert to DB with user_id)
    return {
        "status": "success",
        "message": f"Alert set for {request.alert_type} notifications",
        "update_id": update_id,
        "title": db_update.title,
        "alert_type": request.alert_type,
        "created_at": datetime.utcnow(),
    }


@router.post("/{update_id}/analyze")
def analyze_update(update_id: int, request: dict, db: Session = Depends(get_db)):
    """Analyze a regulatory update with AI based on difficulty level"""
    try:
        # Get update from database
        db_update = db.query(UpdateModel).filter(UpdateModel.id == update_id).first()
        if db_update is None:
            raise HTTPException(status_code=404, detail="Update not found")
        
        difficulty_level = request.get("difficulty_level", "professional")
        if difficulty_level not in ["beginner", "professional", "legal"]:
            difficulty_level = "professional"
        
        print(f"[ANALYZE] Analyzing update {update_id} at {difficulty_level} level")
        
        # Import AI service
        from app.services.ai_service import ai_service
        
        # Generate analysis
        analysis = ai_service.analyze_update(
            update_title=db_update.title,
            update_summary=db_update.short_summary or "",
            full_text=db_update.full_text or db_update.short_summary or "",
            difficulty_level=difficulty_level
        )
        
        return {
            "status": "success",
            "update_id": update_id,
            "difficulty_level": difficulty_level,
            "summary": analysis.get("summary", ""),
            "action_items": analysis.get("action_items", []),
            "risk_level": analysis.get("risk_level", "Medium")
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ANALYZE] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error analyzing update: {str(e)}")