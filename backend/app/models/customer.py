from sqlalchemy import Column, String, Integer, Text, DateTime, func
from app.models import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True)
    wechat_openid = Column(String(100), unique=True, index=True)
    nickname = Column(String(50))
    phone = Column(String(20))
    constitution = Column(String(20))
    constitution_detail = Column(Text)
    created_at = Column(DateTime, server_default=func.now())