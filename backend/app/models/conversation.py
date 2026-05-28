from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, func
from app.models import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, index=True)
    stage = Column(String(30))
    messages = Column(Text)  # legacy: first user message summary
    messages_history = Column(Text)  # JSON array [{role, content, timestamp}]
    stage_history = Column(Text)  # JSON array of stages visited
    constitution_raw = Column(Text)
    constitution_type = Column(String(20))  # AI-identified constitution
    constitution_override = Column(String(20))  # staff manual override
    constitution_confidence = Column(Integer)  # AI confidence 0-100
    scene_input = Column(Text)
    screening_result = Column(String(20))
    channel = Column(String(100))  # QR code channel param
    staff_notes = Column(Text)  # staff manual notes
    staff_tags = Column(Text)  # staff manual tags (comma-separated)
    is_flagged = Column(Boolean, default=False)  # staff flagged for review
    created_at = Column(DateTime, server_default=func.now())