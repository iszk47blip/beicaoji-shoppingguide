from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from jose import JWTError, jwt
from app.config import settings
from app.api.deps import get_current_admin

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    if body.username != settings.admin_username or body.password != settings.admin_password:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    expire = datetime.now(timezone.utc) + timedelta(hours=settings.admin_token_expire_hours)
    payload = {"sub": body.username, "exp": expire, "role": "admin"}
    token = jwt.encode(payload, settings.secret_key, algorithm="HS256")
    return LoginResponse(token=token)


@router.get("/verify")
def verify_token(_admin: str = Depends(get_current_admin)):
    return {"valid": True, "username": _admin}
