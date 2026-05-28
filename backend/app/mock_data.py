"""
Mock data generator for 焙草集 reporting dashboard.
Usage: python -m app.mock_data --days 60 --seed 42
"""
import argparse
import random
import json
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.order import Order
from app.models.product import Product


# ── Constitution types ─────────────────────────────────────────────────────────
CONSTITUTION_TYPES = [
    "气虚质", "血虚质", "阴虚质", "阳虚质",
    "痰湿质", "湿热质", "气郁质", "血瘀质", "特禀质", "平和质"
]

CONSTITUTION_WEIGHTS = [0.08, 0.07, 0.12, 0.10, 0.15, 0.10, 0.08, 0.07, 0.05, 0.18]

# Chinese names for mock customers
FIRST_NAMES = ["王", "李", "张", "刘", "陈", "杨", "赵", "黄", "周", "吴",
               "徐", "孙", "胡", "朱", "高", "林", "何", "郭", "马", "罗"]
LAST_CHARS = ["丽", "梅", "兰", "芳", "军", "勇", "鹏", "伟", "秀", "英",
              "华", "红", "娟", "波", "辉", "静", "波", "杰", "涛", "明"]


def random_constitution(rng: random.Random) -> str:
    return rng.choices(CONSTITUTION_TYPES, weights=CONSTITUTION_WEIGHTS, k=1)[0]


def random_name(rng: random.Random) -> str:
    return rng.choice(FIRST_NAMES) + rng.choice(LAST_CHARS)


def random_phone(rng: random.Random) -> str:
    return f"138{rng.randint(10000000, 99999999)}"


def generate_customers(db: Session, count: int, rng: random.Random) -> list[Customer]:
    """Generate mock customers with random constitution."""
    existing = db.query(Customer).count()
    if existing >= count:
        return db.query(Customer).limit(count).all()

    customers = []
    for i in range(existing, count):
        c = Customer(
            wechat_openid=f"mock_openid_{i:04d}",
            nickname=random_name(rng),
            phone=random_phone(rng),
            constitution=random_constitution(rng),
            created_at=datetime.utcnow() - timedelta(days=rng.randint(1, 30))
        )
        db.add(c)
        customers.append(c)
    db.flush()
    return customers


def generate_conversations(
    db: Session, customers: list[Customer], days: int, rng: random.Random
) -> list[Conversation]:
    """Generate mock conversations: 5-10 per day, 30% get a recommendation."""
    existing = db.query(Conversation).count()
    if existing >= days * 10:
        return db.query(Conversation).limit(days * 10).all()

    conversations = []
    base_date = datetime.utcnow() - timedelta(days=days)

    for day_idx in range(days):
        date = base_date + timedelta(days=day_idx)
        n_conversations = rng.randint(5, 10)

        for _ in range(n_conversations):
            customer = rng.choice(customers)
            hour = rng.randint(9, 21)
            minute = rng.randint(0, 59)
            created_at = date.replace(hour=hour, minute=minute)

            has_recommendation = rng.random() < 0.30

            messages = rng.choice([
                "最近睡眠不好，有什么推荐？",
                "我想调理气血吃什么好？",
                "湿气重喝什么茶？",
                "气虚体质怎么调？",
                "清热解毒的花茶有哪些？",
            ])

            has_recommendation = rng.random() < 0.30

            msgs = [
                {"role": "user", "content": messages, "timestamp": created_at.isoformat()},
            ]
            stages = ["greeting", "constitution", "scene", "recommendation"] if has_recommendation else ["greeting"]

            conv = Conversation(
                customer_id=customer.id,
                stage="recommendation" if has_recommendation else "greeting",
                messages=messages,
                messages_history=json.dumps(msgs, ensure_ascii=False),
                stage_history=json.dumps(stages, ensure_ascii=False),
            )
            db.add(conv)
            conversations.append(conv)

    db.flush()
    return conversations


def generate_orders(
    db: Session, customers: list[Customer], products: list[Product],
    days: int, rng: random.Random
) -> list[Order]:
    """Generate mock orders: 1-5 per day, 50% come from AI recommendations."""
    existing = db.query(Order).count()
    if existing >= days * 5:
        return db.query(Order).limit(days * 5).all()

    orders = []
    base_date = datetime.utcnow() - timedelta(days=days)

    for day_idx in range(days):
        date = base_date + timedelta(days=day_idx)
        n_orders = rng.randint(1, 5)

        for _ in range(n_orders):
            customer = rng.choice(customers)
            hour = rng.randint(9, 21)
            minute = rng.randint(0, 59)
            created_at = date.replace(hour=hour, minute=minute)

            from_ai = rng.random() < 0.50

            # Pick 1-4 products
            n_items = rng.randint(1, 4)
            items = []
            total = 0.0
            for _ in range(n_items):
                prod = rng.choice(products)
                qty = rng.randint(1, 3)
                items.append({
                    "sku_id": prod.sku_id,
                    "name": prod.name,
                    "category": prod.category,
                    "price": prod.price,
                    "quantity": qty
                })
                total += prod.price * qty

            order_no = f"MOCK{date.strftime('%Y%m%d')}{day_idx:04d}{rng.randint(100, 999)}"

            order = Order(
                order_no=order_no,
                customer_id=customer.id,
                customer_nickname=customer.nickname,
                customer_phone=customer.phone,
                total_amount=round(total, 2),
                status="paid",
                items_json=json.dumps(items, ensure_ascii=False),
                conversation_snapshot=json.dumps({"from_ai": from_ai, "msg": "推荐一下"}, ensure_ascii=False) if from_ai else None,
                recommendation_snapshot=json.dumps({"from_ai": from_ai}) if from_ai else None,
                created_at=created_at,
                paid_at=created_at + timedelta(minutes=rng.randint(5, 30))
            )
            db.add(order)
            orders.append(order)

    db.flush()
    return orders


def run(days: int = 60, seed: int = 42, customers: int = 100):
    """Main entry point: generate all mock data."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.config import settings

    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    db = Session()

    rng = random.Random(seed)
    print(f"Generating {days} days of mock data (seed={seed})...")

    # Load real products
    products = db.query(Product).filter(Product.is_active == True).all()
    print(f"  Using {len(products)} real products")

    # Generate customers
    print(f"  Generating {customers} customers...")
    customer_list = generate_customers(db, customers, rng)

    # Generate conversations
    print(f"  Generating {days * 7} conversations...")
    conversations = generate_conversations(db, customer_list, days, rng)

    # Generate orders
    print(f"  Generating ~{days * 3} orders...")
    orders = generate_orders(db, customer_list, products, days, rng)

    db.commit()
    print(f"Done. Created {len(customer_list)} customers, {len(conversations)} conversations, {len(orders)} orders.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate mock data for reporting")
    parser.add_argument("--days", type=int, default=60, help="Number of days to simulate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--customers", type=int, default=100, help="Number of mock customers")
    args = parser.parse_args()

    run(days=args.days, seed=args.seed, customers=args.customers)