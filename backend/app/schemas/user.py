from typing import Optional
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    email: EmailStr
    is_active: Optional[bool] = True
    is_superuser: bool = False
    name: Optional[str] = None
    subscription_type: str = "free"

class UserCreate(UserBase):
    password: str
    name: str

class UserUpdate(UserBase):
    password: Optional[str] = None

class User(UserBase):
    id: int

    class Config:
        from_attributes = True
