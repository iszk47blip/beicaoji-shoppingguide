from sqlalchemy import Column, String, Integer, Text, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

from app.models.product import Product
from app.models.customer import Customer
from app.models.conversation import Conversation

__all__ = ["Base", "Product", "Customer", "Conversation"]


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