# backend/app/api/reports.py
"""
Reporting dashboard API — 6 aggregated endpoints.
All dates are ISO strings (YYYY-MM-DD). Queries are read-only.
"""
import json
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, and_, text
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_admin
from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.order import Order
from app.models.product import Product

router = APIRouter(prefix="/api/staff/reports", tags=["reports"], dependencies=[Depends(get_current_admin)])


def parse_date(s: Optional[str]) -> datetime:
    if not s:
        return datetime.utcnow()
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return datetime.utcnow()


def date_clause(col, start: Optional[str], end: Optional[str]):
    """SQLAlchemy filter for date range on a datetime column."""
    lo = parse_date(start) if start else None
    hi = parse_date(end) if end else None
    if lo and not hi:
        hi = lo + timedelta(days=90)
    if lo and hi:
        return col >= lo and col <= hi
    if lo:
        return col >= lo
    if hi:
        return col <= hi
    return None


# ── GET /api/staff/reports/overview ───────────────────────────────────────────

@router.get("/overview")
def overview(
    start: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    KPI card: total_revenue, order_count, avg_order_value, ai_conversion_rate.
    AI conversion = orders with recommendation_snapshot / total orders.
    """
    lo = parse_date(start) if start else (datetime.utcnow() - timedelta(days=30))
    hi = parse_date(end) if end else datetime.utcnow()
    hi_inclusive = hi + timedelta(days=1)

    orders_q = db.query(Order).filter(
        Order.created_at >= lo,
        Order.created_at < hi_inclusive
    )
    total_revenue = sum(o.total_amount for o in orders_q.all())
    all_orders = list(orders_q.all())
    order_count = len(all_orders)
    ai_orders = sum(1 for o in all_orders if o.recommendation_snapshot)

    return {
        "total_revenue": round(total_revenue, 2),
        "order_count": order_count,
        "avg_order_value": round(total_revenue / order_count, 2) if order_count else 0.0,
        "ai_conversion_rate": round(ai_orders / order_count * 100, 2) if order_count else 0.0
    }


# ── GET /api/staff/reports/revenue-trend ──────────────────────────────────────

@router.get("/revenue-trend")
def revenue_trend(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    granularity: str = Query("day", description="day | week"),
    db: Session = Depends(get_db)
):
    """
    Daily or weekly revenue + order count series.
    Returns [{date, revenue, order_count}, ...]
    """
    lo = parse_date(start) if start else (datetime.utcnow() - timedelta(days=30))
    hi = parse_date(end) if end else datetime.utcnow()
    hi_inclusive = hi + timedelta(days=1)

    orders = db.query(Order).filter(
        Order.created_at >= lo,
        Order.created_at < hi_inclusive
    ).all()

    by_key = {}
    for o in orders:
        d = o.created_at.date()
        if granularity == "week":
            # ISO week: YYYY-Www
            key = d.strftime("%Y-W%W")
        else:
            key = d.isoformat()

        if key not in by_key:
            by_key[key] = {"revenue": 0.0, "order_count": 0}
        by_key[key]["revenue"] += o.total_amount
        by_key[key]["order_count"] += 1

    return [
        {"date": k, "revenue": round(v["revenue"], 2), "order_count": v["order_count"]}
        for k, v in sorted(by_key.items())
    ]


# ── GET /api/staff/reports/product-ranking ────────────────────────────────────

@router.get("/product-ranking")
def product_ranking(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: int = Query(10),
    db: Session = Depends(get_db)
):
    """
    Top products by revenue. Each row:
    {sku_id, name, category, times_recommended, times_purchased, revenue}
    """
    lo = parse_date(start) if start else (datetime.utcnow() - timedelta(days=30))
    hi = parse_date(end) if end else datetime.utcnow()
    hi_inclusive = hi + timedelta(days=1)

    orders = db.query(Order).filter(
        Order.created_at >= lo,
        Order.created_at < hi_inclusive
    ).all()

    # Aggregate from items_json
    stats = {}  # sku_id -> {name, category, revenue, times_purchased}
    for o in orders:
        items = json.loads(o.items_json) if o.items_json else []
        for item in items:
            sku = item.get("sku_id")
            if not sku:
                continue
            if sku not in stats:
                stats[sku] = {"name": item.get("name", sku),
                              "category": item.get("category", "—"),
                              "revenue": 0.0, "times_purchased": 0}
            stats[sku]["revenue"] += (item.get("price", 0) or 0) * (item.get("quantity", 1) or 1)
            stats[sku]["times_purchased"] += 1

    ranked = sorted(stats.values(), key=lambda x: x["revenue"], reverse=True)[:limit]
    return [
        {"sku_id": next((sku for sku, s in stats.items() if s["name"] == r["name"]), r["name"]),
         "name": r["name"], "category": r["category"],
         "times_recommended": 0, "times_purchased": r["times_purchased"],
         "revenue": round(r["revenue"], 2)}
        for r in ranked
    ]


# ── GET /api/staff/reports/conversion-funnel ───────────────────────────────────

@router.get("/conversion-funnel")
def conversion_funnel(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    AI recommendation funnel:
    conversations → recommendations → add-to-cart → purchases.
    Returns {conversations, recommendations, add_to_cart, purchases, rates: {...}}
    """
    lo = parse_date(start) if start else (datetime.utcnow() - timedelta(days=30))
    hi = parse_date(end) if end else datetime.utcnow()
    hi_inclusive = hi + timedelta(days=1)

    all_convs = db.query(Conversation).filter(
        Conversation.created_at >= lo,
        Conversation.created_at < hi_inclusive
    ).all()
    conversations = len(all_convs)
    recommendations = sum(1 for c in all_convs if c.stage and c.stage != "greeting")

    all_orders = db.query(Order).filter(
        Order.created_at >= lo,
        Order.created_at < hi_inclusive
    ).all()
    add_to_cart = sum(1 for o in all_orders if o.conversation_snapshot)
    purchases = sum(1 for o in all_orders if o.recommendation_snapshot)

    def rate(part, whole):
        return round(part / whole * 100, 2) if whole else 0.0

    return {
        "conversations": conversations,
        "recommendations": recommendations,
        "add_to_cart": add_to_cart,
        "purchases": purchases,
        "rates": {
            "recommendation_rate": rate(recommendations, conversations),
            "cart_rate": rate(add_to_cart, recommendations),
            "purchase_rate": rate(purchases, add_to_cart),
            "overall_conversion": rate(purchases, conversations)
        }
    }


# ── GET /api/staff/reports/category-distribution ──────────────────────────────

@router.get("/category-distribution")
def category_distribution(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Revenue by product category.
    Returns [{category, revenue, order_count, percentage}, ...]
    """
    lo = parse_date(start) if start else (datetime.utcnow() - timedelta(days=30))
    hi = parse_date(end) if end else datetime.utcnow()
    hi_inclusive = hi + timedelta(days=1)

    orders = db.query(Order).filter(
        Order.created_at >= lo,
        Order.created_at < hi_inclusive
    ).all()

    cat_stats = {}  # category -> {revenue, order_count}
    for o in orders:
        items = json.loads(o.items_json) if o.items_json else []
        for item in items:
            cat = item.get("category") or "未知"
            if cat not in cat_stats:
                cat_stats[cat] = {"revenue": 0.0, "order_count": 0}
            cat_stats[cat]["revenue"] += (item.get("price", 0) or 0) * (item.get("quantity", 1) or 1)
            cat_stats[cat]["order_count"] += 1

    total_revenue = sum(v["revenue"] for v in cat_stats.values()) or 1.0
    return [
        {"category": cat, "revenue": round(v["revenue"], 2),
         "order_count": v["order_count"],
         "percentage": round(v["revenue"] / total_revenue * 100, 2)}
        for cat, v in sorted(cat_stats.items(), key=lambda x: x[1]["revenue"], reverse=True)
    ]


# ── GET /api/staff/reports/constitution-distribution ──────────────────────────

@router.get("/constitution-distribution")
def constitution_distribution(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Customer count and avg order value grouped by constitution type.
    Returns [{constitution_type, customer_count, avg_order_value}, ...]
    """
    lo = parse_date(start) if start else (datetime.utcnow() - timedelta(days=30))
    hi = parse_date(end) if end else datetime.utcnow()
    hi_inclusive = hi + timedelta(days=1)

    from app.models.order import Order
    customers = db.query(Customer).all()

    const_stats = {}  # constitution -> {count, total_revenue}
    for c in customers:
        ct = c.constitution or "未知"
        if ct not in const_stats:
            const_stats[ct] = {"count": 0, "total": 0.0}

        orders = db.query(Order).filter(
            Order.customer_id == c.id,
            Order.status == "paid",
            Order.created_at >= lo,
            Order.created_at < hi_inclusive
        ).all()

        if orders:
            const_stats[ct]["count"] += 1
            const_stats[ct]["total"] += sum(o.total_amount for o in orders)

    return [
        {"constitution_type": ct,
         "customer_count": v["count"],
         "avg_order_value": round(v["total"] / v["count"], 2) if v["count"] else 0.0}
        for ct, v in sorted(const_stats.items(), key=lambda x: x[1]["count"], reverse=True)
    ]