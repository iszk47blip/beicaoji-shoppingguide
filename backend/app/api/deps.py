# backend/app/api/deps.py
from app.models import get_session

def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()