from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User

SECRET = "dev-secret"
ALGO = "HS256"
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def hash_password(password: str) -> str:
    return pwd.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd.verify(password, hashed)


def issue_token(user_id: str) -> str:
    return jwt.encode({"sub": user_id, "exp": datetime.utcnow() + timedelta(days=7)}, SECRET, algorithm=ALGO)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(credentials.credentials, SECRET, algorithms=[ALGO])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    user = db.get(User, payload.get("sub"))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return user
