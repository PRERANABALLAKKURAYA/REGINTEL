from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.authority import Authority as AuthorityModel
from app.schemas.authority import Authority, AuthorityCreate
from app.scrapers.source_registry import AUTHORITY_SOURCE_REGISTRY

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=List[Authority])
def read_authorities(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    authorities = db.query(AuthorityModel).offset(skip).limit(limit).all()
    return authorities

@router.get("/sources")
def read_authority_sources():
    """
    Returns configured official data-source endpoints for all 7 regulatory authorities.
    Includes API/RSS/HTML source types where available.
    """
    return {
        "count": len(AUTHORITY_SOURCE_REGISTRY),
        "authorities": AUTHORITY_SOURCE_REGISTRY,
    }

@router.post("/", response_model=Authority)
def create_authority(authority: AuthorityCreate, db: Session = Depends(get_db)):
    db_authority = AuthorityModel(**authority.dict())
    db.add(db_authority)
    db.commit()
    db.refresh(db_authority)
    return db_authority

@router.get("/{authority_id}", response_model=Authority)
def read_authority(authority_id: int, db: Session = Depends(get_db)):
    db_authority = db.query(AuthorityModel).filter(AuthorityModel.id == authority_id).first()
    if db_authority is None:
        raise HTTPException(status_code=404, detail="Authority not found")
    return db_authority
