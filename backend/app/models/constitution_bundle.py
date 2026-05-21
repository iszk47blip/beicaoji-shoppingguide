# backend/app/models/constitution_bundle.py
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from app.models import Base
from datetime import datetime

class ConstitutionBundle(Base):
    __tablename__ = "constitution_bundle"
    __table_args__ = (UniqueConstraint("constitution_type", "sku_id"),)

    id = Column(Integer, primary_key=True)
    constitution_type = Column(String(20), nullable=False, index=True)
    sku_id = Column(String(20), nullable=False, index=True)
    sort_order = Column(Integer, default=0)
    description = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)


class HotProduct(Base):
    __tablename__ = "hot_product"

    id = Column(Integer, primary_key=True)
    sku_id = Column(String(20), nullable=False, unique=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)