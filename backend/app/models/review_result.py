from sqlalchemy import Column, String, Integer, Text, DateTime, func
from app.models import Base


class ReviewResult(Base):
    __tablename__ = "review_results"

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, index=True)
    problems_found = Column(Text)  # JSON array of problem objects
    suggestions = Column(Text)  # JSON array of suggestion objects
    quality_score = Column(Integer)  # 1-10 rating
    reviewed_at = Column(DateTime, server_default=func.now())
