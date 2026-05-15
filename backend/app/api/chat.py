# backend/app/api/chat.py
import json
from fastapi import APIRouter, Depends, Body
from pydantic import BaseModel
from app.services.dialogue_engine import DialogueEngine
from app.services.product_service import ProductService
from app.services.recommend_engine import RecommendEngine
from app.api.deps import get_db

router = APIRouter(prefix="/api/chat", tags=["chat"])
engine = DialogueEngine()

# In-memory session store (single-process only - sufficient for MVP)
_session_store: dict[str, dict] = {}


class SendRequest(BaseModel):
    session_id: str
    message: str = ""


class ResetRequest(BaseModel):
    session_id: str


def _describe_recommendation(engine: DialogueEngine, state: dict, rec: dict) -> str:
    """Use LLM to naturally describe the engine's recommendation results."""
    constitution = rec.get("constitution", {})
    ctype = constitution.get("constitution_type", "平和质")
    products = rec.get("bundle", [])
    CAT_CN = {"biscuit": "饼干", "bread": "面包", "tea": "茶", "toy": "香囊"}
    product_list = "\n".join(
        f"- {CAT_CN.get(p.get('category', ''), '')}「{p.get('name', '')}」成分：{p.get('ingredients', '')}"
        for p in products
    )
    ctx = engine._state_context(state)
    instruction = (
        f"顾客偏{ctype}体质。推荐产品：\n\n{product_list}\n\n"
        "逐款解释为什么适合他（结合成分与体质），不要加品类标签，不要问品类偏好，不要建议到店。"
        "结尾问'你觉得这几个怎么样？'。不用markdown。"
    )
    msg = engine._chat(instruction, ctx)
    return msg


def _search_products(db, query: str, state: dict = None, limit: int = 4) -> dict:
    """Free-text search across product names, ingredients, and scene tags."""
    from app.models.product import Product
    products = db.query(Product).filter(Product.is_active == True).all()
    keywords = query.strip()
    scored = []
    for p in products:
        score = 0
        name = p.name or ""
        ingredients = p.ingredients or ""
        scene_tags = p.scene_tags or ""
        if keywords in name: score += 10
        if keywords in ingredients: score += 5
        if keywords in scene_tags: score += 5
        for kw in keywords:
            if kw in name: score += 2
            if kw in ingredients: score += 1
            if kw in scene_tags: score += 1
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    bundle = [{"name": p.name, "sku_id": p.sku_id, "category": p.category,
               "ingredients": p.ingredients or "", "price": p.price or 0}
              for _, p in scored[:limit]]

    # Use stored constitution data if available, otherwise show generic label
    ctype = "为你挑选"
    cdesc = f"根据「{keywords[:20]}」找到以下产品"
    if state:
        stored = state.get("recommendation", {})
        stored_ctype = stored.get("constitution", {}).get("constitution_type", "")
        if stored_ctype and stored_ctype != "为你挑选":
            ctype = stored_ctype
            cdesc = stored.get("constitution", {}).get("description", cdesc)

    return {"bundle": bundle, "products": bundle,
            "constitution": {"constitution_type": ctype, "description": cdesc}}

def _describe_fallback(engine: DialogueEngine, state: dict, rec: dict) -> str:
    """When no products perfectly match the constitution+scene, explain and offer the report."""
    ctype = rec.get("constitution", {}).get("constitution_type", "平和质")
    ctx = engine._state_context(state)
    instruction = (
        f"顾客偏{ctype}体质，但店里的产品没有完美匹配他当前的情况。"
        "请温和地告诉他：店里虽然没有专门针对他情况的产品，但已为他生成了一份调理报告，"
        "里面有详细的食养建议和生活调养指导。"
        "建议他点击'查看完整调理报告'查看。语气温暖真诚，不要用markdown。"
    )
    return engine._chat(instruction, ctx)


def _describe_search_result(engine: DialogueEngine, state: dict, rec: dict, query: str) -> str:
    """Use LLM to naturally describe search results."""
    products = rec.get("bundle", [])
    CAT_CN = {"biscuit": "饼干", "bread": "面包", "tea": "茶", "toy": "香囊"}
    product_list = "\n".join(
        f"- {CAT_CN.get(p.get('category', ''), '')}「{p.get('name', '')}」成分：{p.get('ingredients', '')}"
        for p in products
    )
    ctx = engine._state_context(state)
    instruction = (
        f"顾客搜索「{query}」，找到：\n\n{product_list}\n\n"
        "逐款简短介绍，结尾问'有感兴趣的吗？'。不用markdown。"
    )
    return engine._chat(instruction, ctx)


@router.post("/send")
def send_message(req: SendRequest, db=Depends(get_db)):
    session_id = req.session_id
    message = req.message
    state_key = f"chat:{session_id}"
    state = _session_store.get(state_key) or {"stage": "greeting"}

    if not message:
        result = engine.get_bot_message(state)
        result["intent"] = "continue_flow"
    else:
        result = engine.process_user_message(state, message)

    recommendation = None
    catalog = None
    intent = result.get("intent", "continue_flow")

    # Intent routing: product search or catalog display at any stage
    if intent == "search_product" and message:
        rec = _search_products(db, message, state)
        if rec.get("bundle"):
            recommendation = rec
            try:
                result["message"] = _describe_search_result(engine, state, rec, message)
            except Exception:
                pass  # Keep original message if LLM call fails
        elif state.get("recommendation"):
            # Vague query like "再推荐几个" with no product keywords —
            # fall back to recommend engine using existing constitution data
            product_svc = ProductService(db)
            rec_engine = RecommendEngine(product_svc)
            recommendation = rec_engine.recommend(
                state.get("constitution_raw", "{}"),
                state.get("scene_raw", "")
            )
            if recommendation and recommendation.get("bundle"):
                try:
                    result["message"] = _describe_recommendation(engine, state, recommendation)
                except Exception:
                    pass
    elif intent == "show_catalog":
        product_svc = ProductService(db)
        catalog = product_svc.get_constitution_catalog()

    # Existing stage-based routing
    if result.get("stage") == "recommend" and not recommendation:
        product_svc = ProductService(db)
        rec_engine = RecommendEngine(product_svc)
        recommendation = rec_engine.recommend(
            state.get("constitution_raw", "{}"),
            result.get("scene_raw", "")
        )
        if recommendation.get("bundle"):
            try:
                if recommendation.get("no_match"):
                    result["message"] = _describe_fallback(engine, state, recommendation)
                else:
                    result["message"] = _describe_recommendation(engine, state, recommendation)
            except Exception:
                pass
    elif result.get("stage") == "catalog" and not catalog:
        product_svc = ProductService(db)
        catalog = product_svc.get_constitution_catalog()

    # Fix quick_replies and stage when recommendation or catalog content is shown
    if recommendation:
        result["quick_replies"] = ["推荐更多产品", "重新了解体质", "看看产品目录"]
        result["stage"] = "recommend"
    elif catalog:
        result["quick_replies"] = ["饼干", "面包", "茶", "香囊", "帮我看看体质"]
        result["stage"] = "catalog"

    new_state = {**state, **result}
    if recommendation:
        new_state["recommendation"] = recommendation
    if catalog:
        new_state["catalog"] = catalog
    _session_store[state_key] = new_state

    return {
        "message": result.get("message", ""),
        "stage": result.get("stage", "greeting"),
        "quick_replies": result.get("quick_replies"),
        "recommendation": recommendation,
        "catalog": catalog,
        "screening_result": new_state.get("screening_result"),
    }


@router.post("/reset")
def reset_session(req: ResetRequest):
    state_key = f"chat:{req.session_id}"
    _session_store.pop(state_key, None)
    return {"status": "ok"}
