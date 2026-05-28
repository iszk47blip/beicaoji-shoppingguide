from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.models import get_session
from app.config import settings

security = HTTPBearer()


def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()


def get_current_admin(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username != settings.admin_username:
            raise HTTPException(status_code=401, detail="无效的认证信息")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的认证信息")