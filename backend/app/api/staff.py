# backend/app/api/staff.py
import asyncio
import io
import json
import time
import openpyxl
from fastapi import APIRouter, Body, Depends, UploadFile, File, HTTPException
from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.product import Product
from app.models.order import Order
from app.api.deps import get_db
from app.services.data_importer import parse_excel_columns, merge_product, import_products_from_wb

router = APIRouter(prefix="/api/staff", tags=["staff"])


@router.get("/products")
def list_products(
    page: int = 1,
    page_size: int = 50,
    category: str = None,
    stock_zero: bool = False,
    q: str = None,
    db=Depends(get_db)
):
    """搜索商品，支持按名称、商品条码、成分关键词搜索。"""
    stmt = db.query(Product)
    if category:
        stmt = stmt.filter(Product.category == category)
    if stock_zero:
        stmt = stmt.filter(Product.stock <= 0)
    if q:
        q_lower = q.lower()
        stmt = stmt.filter(
            (Product.name.ilike(f"%{q}%")) |
            (Product.sku_id.ilike(f"%{q}%")) |
            (Product.ingredients.ilike(f"%{q}%")) |
            (Product.category.ilike(f"%{q}%"))
        )
    total = stmt.count()
    offset = (page - 1) * page_size
    products = stmt.order_by(Product.category, Product.name).offset(offset).limit(page_size).all()
    return {
        "total": total,
        "products": [
            {"id": p.id, "sku_id": p.sku_id, "name": p.name, "category": p.category,
             "price": p.price, "stock": p.stock, "is_active": p.is_active,
             "ingredients": p.ingredients}
            for p in products
        ]
    }


@router.get("/products/selected")
def get_selected_products(ids: str, db=Depends(get_db)):
    """根据逗号分隔的 id 列表查询商品，用于批量操作前确认"""
    id_list = [int(x) for x in ids.split(",") if x.isdigit()]
    products = db.query(Product).filter(Product.id.in_(id_list)).all()
    return {
        "products": [
            {"id": p.id, "sku_id": p.sku_id, "name": p.name, "category": p.category,
             "price": p.price, "stock": p.stock, "is_active": p.is_active}
            for p in products
        ]
    }


@router.patch("/products/batch-stock-relative")
def batch_update_stock_relative(updates: list[dict], db=Depends(get_db)):
    """批量相对更新库存，如 [{"sku_id": "P26...", "delta": 5}] 或 [{"sku_id": "P26...", "stock": 10}]"""
    updated = []
    for item in updates:
        sku = item.get("sku_id")
        if not sku:
            continue
        product = db.query(Product).filter(Product.sku_id == sku).first()
        if not product:
            continue
        delta = item.get("delta")
        stock = item.get("stock")
        if delta is not None:
            product.stock = max(0, (product.stock or 0) + int(delta))
        elif stock is not None:
            product.stock = max(0, int(stock))
        updated.append({"sku_id": sku, "stock": product.stock})
    db.commit()
    return {"updated": len(updated), "items": updated}


@router.get("/categories")
def list_categories(db=Depends(get_db)):
    cats = db.query(Product.category).distinct().all()
    return {"categories": [c[0] for c in cats if c[0]]}

@router.post("/products/import")
async def import_excel(file: UploadFile = File(...), db=Depends(get_db)):
    """上传有赞导出的商品库 Excel，增量导入（主数据用导入值，Tag 保留/补全）"""
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 文件")
    content = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(content))

    result = import_products_from_wb(db, wb)
    return {
        "imported": result["imported"],
        "updated": result["updated"],
        "tag_filled": result["tag_filled"],
        "skipped_garbled": result["skipped_garbled"],
        "errors": []
    }


@router.post("/products/generate-tags")
async def generate_missing_tags(db=Depends(get_db)):
    """对所有 scene_tags 为空的有效产品批量生成标签"""
    products = db.query(Product).filter(
        Product.is_active == True,
        Product.stock > 0,
        (Product.scene_tags == None) | (Product.scene_tags == "")
    ).all()

    gen = TagGenerator()
    success = 0
    failed = []
    for p in products:
        try:
            tags = gen.generate(p.name, p.ingredients or "")
            p.scene_tags = tags["scene_tags"]
            p.contraindication_tags = tags["contraindication_tags"]
            db.commit()
            success += 1
        except Exception as e:
            await asyncio.sleep(5)
            try:
                tags = gen.generate(p.name, p.ingredients or "")
                p.scene_tags = tags["scene_tags"]
                p.contraindication_tags = tags["contraindication_tags"]
                db.commit()
                success += 1
            except Exception as e2:
                failed.append({"sku_id": p.sku_id, "name": p.name, "reason": str(e2)[:100]})
                if len(failed) % 10 == 0:
                    db.commit()

    db.commit()
    return {"total": len(products), "success": success, "failed": failed}


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


# ── Orders ──────────────────────────────────────────────────────────────────

def _order_dict(o: Order) -> dict:
    """Serialize an Order row into a clean JSON-safe dict."""
    return {
        "id": o.id,
        "order_no": o.order_no,
        "customer_id": o.customer_id,
        "customer_nickname": o.customer_nickname,
        "customer_phone": o.customer_phone,
        "total_amount": o.total_amount,
        "status": o.status,
        "items": json.loads(o.items_json) if o.items_json else [],
        "conversation_snapshot": json.loads(o.conversation_snapshot) if o.conversation_snapshot else None,
        "recommendation_snapshot": json.loads(o.recommendation_snapshot) if o.recommendation_snapshot else None,
        "constitution_snapshot": json.loads(o.constitution_snapshot) if o.constitution_snapshot else None,
        "created_at": str(o.created_at) if o.created_at else None,
        "paid_at": str(o.paid_at) if o.paid_at else None,
    }


@router.post("/orders")
def create_order(data: dict, db=Depends(get_db)):
    """Create/save an order when customer completes checkout in mini-program."""
    existing = db.query(Order).filter(Order.order_no == data.get("order_no")).first()
    if existing:
        raise HTTPException(status_code=409, detail="订单号已存在")
    order = Order(
        order_no=data["order_no"],
        customer_nickname=data.get("customer_nickname"),
        customer_phone=data.get("customer_phone"),
        total_amount=float(data.get("total_amount", 0)),
        items_json=json.dumps(data.get("items", []), ensure_ascii=False),
        conversation_snapshot=json.dumps(data.get("conversation_snapshot"), ensure_ascii=False) if data.get("conversation_snapshot") else None,
        recommendation_snapshot=json.dumps(data.get("recommendation_snapshot"), ensure_ascii=False) if data.get("recommendation_snapshot") else None,
        constitution_snapshot=json.dumps(data.get("constitution_snapshot"), ensure_ascii=False) if data.get("constitution_snapshot") else None,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return _order_dict(order)


@router.get("/orders")
def list_orders(page: int = 1, page_size: int = 20, status: str = None, db=Depends(get_db)):
    """List all orders, newest first. Status filter: pending/paid/cancelled/refunded."""
    stmt = db.query(Order)
    if status:
        stmt = stmt.filter(Order.status == status)
    total = stmt.count()
    offset = (page - 1) * page_size
    orders = stmt.order_by(Order.created_at.desc()).offset(offset).limit(page_size).all()
    return {"total": total, "orders": [_order_dict(o) for o in orders]}


@router.get("/orders/{order_id}")
def order_detail(order_id: int, db=Depends(get_db)):
    """Get order detail with full conversation/recommendation/constitution snapshots."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    return _order_dict(order)


@router.patch("/orders/{order_id}/status")
def update_order_status(order_id: int, status: str, db=Depends(get_db)):
    """Update order status: paid/cancelled/refunded"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    valid = ("paid", "cancelled", "refunded")
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"状态必须是: {', '.join(valid)}")
    order.status = status
    if status == "paid":
        from datetime import datetime
        order.paid_at = datetime.utcnow()
    db.commit()
    return _order_dict(order)


@router.get("/constitution-bundles")
def get_constitution_bundles(db=Depends(get_db)):
    """获取所有体质套餐，按体质类型分组"""
    from app.models.constitution_bundle import ConstitutionBundle
    from app.models.product import Product
    bundles = db.query(ConstitutionBundle).order_by(ConstitutionBundle.sort_order).all()
    grouped = {}
    for b in bundles:
        prod = db.query(Product).filter_by(sku_id=b.sku_id).first()
        grouped.setdefault(b.constitution_type, []).append({
            "sku_id": b.sku_id,
            "sort_order": b.sort_order,
            "description": b.description,
            "name": prod.name if prod else b.sku_id,
            "category": prod.category if prod else "—",
        })
    return grouped


@router.put("/constitution-bundles/{ctype}")
def put_constitution_bundle(ctype: str, data: dict = Body(...), db=Depends(get_db)):
    """整体替换某体质类型的套餐"""
    from app.models.constitution_bundle import ConstitutionBundle
    db.query(ConstitutionBundle).filter(ConstitutionBundle.constitution_type == ctype).delete()
    for i, p in enumerate(data.get("products", [])):
        item = ConstitutionBundle(
            constitution_type=ctype,
            sku_id=p["sku_id"],
            sort_order=p.get("sort_order", i),
            description=p.get("description", "")
        )
        db.add(item)
    db.commit()
    return {"status": "ok", "count": len(data.get("products", []))}


@router.get("/hot-products")
def get_hot_products(db=Depends(get_db)):
    """获取主推产品列表"""
    from app.models.constitution_bundle import HotProduct
    from app.models.product import Product
    items = db.query(HotProduct).order_by(HotProduct.sort_order).all()
    return [
        {"sku_id": h.sku_id, "sort_order": h.sort_order,
         "name": db.query(Product).filter_by(sku_id=h.sku_id).first().name if db.query(Product).filter_by(sku_id=h.sku_id).first() else h.sku_id,
         "category": db.query(Product).filter_by(sku_id=h.sku_id).first().category if db.query(Product).filter_by(sku_id=h.sku_id).first() else "—"}
        for h in items
    ]


@router.put("/hot-products")
def put_hot_products(data: dict = Body(...), db=Depends(get_db)):
    """整体替换主推产品列表"""
    from app.models.constitution_bundle import HotProduct
    db.query(HotProduct).delete()
    for i, p in enumerate(data.get("products", [])):
        item = HotProduct(sku_id=p["sku_id"], sort_order=p.get("sort_order", i))
        db.add(item)
    db.commit()
    return {"status": "ok", "count": len(data.get("products", []))}