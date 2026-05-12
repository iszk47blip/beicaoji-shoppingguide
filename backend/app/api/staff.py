# backend/app/api/staff.py
from fastapi import APIRouter, Depends
from app.models.customer import Customer
from app.models.conversation import Conversation
from app.api.deps import get_db

router = APIRouter(prefix="/api/staff", tags=["staff"])

@router.get("/customers")
def list_customers(page: int = 1, page_size: int = 20, db=Depends(get_db)):
    offset = (page - 1) * page_size
    customers = db.query(Customer).order_by(Customer.created_at.desc()).offset(offset).limit(page_size).all()
    return {"customers": [
        {"id": c.id, "nickname": c.nickname, "phone": c.phone,
         "constitution": c.constitution, "created_at": str(c.created_at)}
        for c in customers
    ]}

@router.get("/customers/{customer_id}")
def customer_detail(customer_id: int, db=Depends(get_db)):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    conversations = db.query(Conversation).filter(Conversation.customer_id == customer_id).all()
    return {"customer": customer, "conversations": conversations}