from sqlalchemy import Column, String, Integer, Text, Float, DateTime, func, ForeignKey
from sqlalchemy.orm import relationship
from app.models import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    order_no = Column(String(32), unique=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)
    customer_nickname = Column(String(50))
    customer_phone = Column(String(20))
    total_amount = Column(Float, default=0)
    status = Column(String(20), default="pending")  # pending / paid / cancelled / refunded
    items_json = Column(Text)   # JSON array of {sku_id, name, category, price, quantity}
    conversation_id = Column(Integer, ForeignKey("conversations.id"), index=True)
    conversation_snapshot = Column(Text)  # JSON of full conversation messages
    recommendation_snapshot = Column(Text)  # JSON of last recommendation
    constitution_snapshot = Column(Text)  # JSON of constitution analysis
    created_at = Column(DateTime, server_default=func.now())
    paid_at = Column(DateTime, nullable=True)