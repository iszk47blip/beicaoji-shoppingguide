from sqlalchemy import Column, String, Integer, Text, DateTime, func
from app.models import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, index=True)
    stage = Column(String(30))
    messages = Column(Text)
    constitution_raw = Column(Text)
    scene_input = Column(Text)
    screening_result = Column(String(20))
    created_at = Column(DateTime, server_default=func.now())