from sqlalchemy import Column, String, Integer, Float, Boolean, Text
from app.models import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    sku_id = Column(String(20), unique=True, nullable=False, index=True)
    youzan_item_id = Column(String(50))
    youzan_item_url = Column(String(500))
    category = Column(String(20), nullable=False)
    feature_tag = Column(String(50))
    name = Column(String(100), nullable=False)
    ingredients = Column(Text)
    scene_tags = Column(Text)
    sales_script = Column(Text)
    contraindication_tags = Column(Text)
    price = Column(Float, default=0)
    is_active = Column(Boolean, default=True)