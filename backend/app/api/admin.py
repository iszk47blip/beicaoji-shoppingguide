from fastapi import APIRouter, Depends
from app.models.product import Product
from app.models.customer import Customer
from app.api.deps import get_db

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/stats")
def stats(db=Depends(get_db)):
    products_count = db.query(Product).filter(Product.is_active == True).count()
    customers_count = db.query(Customer).count()
    with_tags = db.query(Product).filter(
        Product.is_active == True, Product.scene_tags != ""
    ).count()
    return {
        "products_count": products_count,
        "customers_count": customers_count,
        "tag_completion_rate": round(with_tags / products_count * 100, 1) if products_count else 0,
    }

@router.put("/products/{product_id}")
def update_product(product_id: int, data: dict, db=Depends(get_db)):
    """更新商品标签、品类、价格等"""
    allowed = ["scene_tags", "contraindication_tags", "category",
               "feature_tag", "price", "is_active"]
    update_data = {k: v for k, v in data.items() if k in allowed}
    db.query(Product).filter(Product.id == product_id).update(update_data)
    db.commit()
    return {"status": "ok"}
