from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from jose import jwt, JWTError
from fastapi import HTTPException, status
import hashlib

from backend.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_HOURS, USERS
from backend.rbac.models import TokenData, Role

def verify_password(plain: str, hashed: str) -> bool:
    return hashlib.sha256(plain.encode()).hexdigest() == hashed

def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    if email not in USERS:
        return None
    user = USERS[email]
    if not verify_password(password, user["password_hash"]):
        return None
    return user

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS)
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("email")
        role_str: str = payload.get("role")
        exp: int = payload.get("exp")
        
        if email is None or role_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token_data = TokenData(email=email, role=Role(role_str), exp=exp)
        return token_data
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(token: str) -> dict:
    token_data = decode_token(token)
    if token_data.email not in USERS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return USERS[token_data.email]
