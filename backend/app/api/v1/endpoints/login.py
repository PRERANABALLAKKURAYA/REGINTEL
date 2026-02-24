from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api import deps
from app.core import security
from app.models.user import User
from app.schemas.token import Token

router = APIRouter()

@router.post("/login/access-token", response_model=Token)
def login_access_token(
    db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not security.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(minutes=security.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


from pydantic import BaseModel


class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str


@router.post("/register", response_model=Token)
def register(req: RegisterRequest, db: Session = Depends(deps.get_db)) -> Any:
    user = db.query(User).filter(User.email == req.email).first()
    if user:
        raise HTTPException(status_code=400, detail="Email already registered.")
    user = User(
        email=req.email,
        name=req.name,
        password_hash=security.get_password_hash(req.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    access_token_expires = timedelta(minutes=security.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
