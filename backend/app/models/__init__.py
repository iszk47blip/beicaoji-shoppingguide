from sqlalchemy import Column, String, Integer, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

from app.models.product import Product
from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.order import Order
from app.models.constitution_bundle import ConstitutionBundle, HotProduct
from app.models.review_result import ReviewResult

__all__ = ["Base", "Product", "Customer", "Conversation", "Order",
           "ConstitutionBundle", "HotProduct", "ReviewResult"]


def init_db():
    from sqlalchemy import create_engine
    from app.config import settings
    engine = create_engine(settings.database_url)
    Base.metadata.create_all(engine)
    return engine


Session = None  # lazy initialization


def get_session():
    global Session
    if Session is None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.config import settings
        engine = create_engine(settings.database_url)
        Session = sessionmaker(bind=engine)
    return Session()