from datetime import datetime, timedelta
from typing import Any, Union, Optional
from jose import jwt
import hashlib
import secrets
from app.core.config import settings

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Simple verification: hash the plain password and compare
    parts = hashed_password.split("$")
    if len(parts) < 3:
        return False
    salt = parts[1]
    stored_hash = parts[2]
    # Recalculate hash with the extracted salt
    calc_hash = hashlib.pbkdf2_hmac('sha256', plain_password.encode(), salt.encode(), 100000).hex()
    return calc_hash == stored_hash

def get_password_hash(password: str) -> str:
    # Simple PBKDF2 hashing
    salt = secrets.token_hex(16)
    hash_value = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
    return f"pbkdf2${salt}${hash_value}"
