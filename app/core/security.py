from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import jwt
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password:str)->str:
    return pwd_context.hash(password)

def verify_password(plain_password:str, hashed_password:str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_jwt(subject:str, *, expires_delta: timedelta, refresh: bool = False) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now+expires_delta).timestamp()),
        "typ": "refresh" if refresh else "access",
    }
    key = settings.REFRESH_SECRET_KEY if refresh else settings.ACCESS_SECRET_KEY
    return jwt.encode(payload, key, algorithm=settings.ALGORITHM)


def decode_jwt(token: str, *, refresh: bool = False) -> dict:
    key = settings.REFRESH_SECRET_KEY if refresh else settings.ACCESS_SECRET_KEY
    return jwt.decode(token, key, algorithms=[settings.ALGORITHM])