# backend/tests/test_recommend_engine.py
from app.services.recommend_engine import RecommendEngine


def test_recommend_bundle_cross_category(test_db_with_products):
    from app.services.product_service import ProductService
    svc = ProductService(test_db_with_products)
    engine = RecommendEngine(svc)
    result = engine.recommend(
        '{"qi_deficiency": "是，经常觉得累、不想说话"}',
        "我最近总是睡不好，容易醒"
    )
    assert result["constitution"]["constitution_type"] is not None
    assert len(result["bundle"]) >= 1
    cats = [p["category"] for p in result["bundle"]]
    assert len(cats) == len(set(cats))