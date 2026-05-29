# backend/app/api/chat.py
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Body
from pydantic import BaseModel
from app.services.dialogue_engine import DialogueEngine, Stage
from app.services.product_service import ProductService
from app.services.recommend_engine import RecommendEngine
from app.api.deps import get_db
from app.models.customer import Customer
from app.models.conversation import Conversation

router = APIRouter(prefix="/api/chat", tags=["chat"])
engine = DialogueEngine()

# In-memory session store (single-process only - sufficient for MVP)
_session_store: dict[str, dict] = {}


class SendRequest(BaseModel):
    session_id: str
    message: str = ""
    channel: str = ""  # QR code channel param


class ResetRequest(BaseModel):
    session_id: str


def _describe_recommendation(engine: DialogueEngine, state: dict, rec: dict) -> str:
    """Return a short summary pointing to the report for details."""
    constitution = rec.get("constitution", {})
    ctype = constitution.get("constitution_type", "平和质")
    fixed = rec.get("fixed_bundle", [])
    llm_recs = rec.get("llm_recommendations", [])
    total = len(fixed) + len(llm_recs)

    tips = {
        "气虚质": "平时注意别太累，适当吃点补气的食物",
        "阳虚质": "注意保暖，少吃生冷的，多晒太阳",
        "阴虚质": "少熬夜，多吃润燥的食物，多喝水",
        "痰湿质": "饮食清淡些，多运动出出汗会舒服很多",
        "湿热质": "少吃辛辣油炸，多喝清热利湿的茶",
        "气郁质": "多出门走走，心情不好的时候找人聊聊天",
        "血瘀质": "适当运动促进循环，少吃寒凉的东西",
        "血虚质": "多吃补血的食物，别太操劳，保证睡眠",
        "特禀质": "注意避开过敏原，换季时多加小心",
        "平和质": "保持现在的生活习惯就好，注意均衡饮食",
    }

    return (
        f"你是偏{ctype}体质。我为你搭配了{total}款适合的产品～\n\n"
        f"💡 {tips.get(ctype, '保持健康的生活习惯')}\n\n"
        f"详细的产品介绍和食养建议都在调理报告里了，点击下方查看吧~"
    )


# Layer 1: everyday language → category filter
CATEGORY_ALIAS = {
    "零食": ["biscuit", "bread"], "点心": ["biscuit", "bread"], "吃的": ["biscuit", "bread"],
    "小食": ["biscuit", "bread"], "饼干": ["biscuit"], "面包": ["bread"],
    "喝的": ["tea"], "饮品": ["tea"], "饮料": ["tea"], "茶": ["tea"], "泡的": ["tea"],
    "香囊": ["toy"], "挂件": ["toy"], "装饰": ["toy"], "摆设": ["toy"], "玩偶": ["toy"],
}

# Layer 2: semantic keyword expansion for search
SEARCH_SYNONYMS = {
    "零食": ["零食", "点心", "小食", "休闲"],
    "点心": ["点心", "零食", "糕点", "小食"],
    "吃的": ["零食", "点心", "小食", "糕点"],
    "喝的": ["茶", "饮品", "饮料", "泡的"],
    "上火": ["上火", "清热", "降火", "燥热"],
    "睡不好": ["睡眠", "安神", "助眠", "失眠"],
    "累": ["疲劳", "乏力", "补气", "精力"],
    "消化不好": ["消食", "健脾", "肠胃", "消化不良"],
}

# Layer 3: category consumption attributes — non-edible categories
NON_EDIBLE = {"toy"}


def _search_products(db, query: str, state: dict = None, limit: int = 4) -> dict:
    """Semantic product search with category filtering and synonym expansion."""
    from app.models.product import Product
    products = db.query(Product).filter(Product.is_active == True).all()
    keywords = query.strip()

    # ---- Layer 1: filter by category if everyday language detected ----
    allowed_cats = None
    for alias, cats in CATEGORY_ALIAS.items():
        if alias in keywords:
            allowed_cats = cats
            break

    # ---- Layer 2: expand keywords with synonyms ----
    search_words = SEARCH_SYNONYMS.get(keywords, [keywords])

    # ---- Layer 3: detect consumption intent and filter non-edible ----
    edible_only = any(w in keywords for w in ["零食", "点心", "吃的", "小食", "喝的", "饮品", "饮料"])

    scored = []
    for p in products:
        if allowed_cats and p.category not in allowed_cats:
            continue
        if edible_only and p.category in NON_EDIBLE:
            continue

        score = 0
        name = p.name or ""
        ingredients = p.ingredients or ""
        scene_tags = p.scene_tags or ""

        for kw in search_words:
            if kw in name: score += 10
            if kw in ingredients: score += 5
            if kw in scene_tags: score += 5
        # Also match individual characters for Chinese
        for ch in keywords:
            if ch in name: score += 2
            if ch in ingredients: score += 1
            if ch in scene_tags: score += 1

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
        f"顾客偏{ctype}体质。店里的产品不完全匹配他的情况。"
        "用1-2句话温和告知：已为你生成了一份调理报告，里面有食养建议和生活调养指导，点击下方报告查看。语气温暖。"
    )
    return engine._chat(instruction, ctx)


def _describe_search_result(engine: DialogueEngine, state: dict, rec: dict, query: str) -> str:
    """Use LLM to naturally describe search results, respecting category intent."""
    products = rec.get("bundle", [])
    CAT_CN = {"biscuit": "饼干", "bread": "面包", "tea": "茶", "toy": "香囊"}
    product_list = "\n".join(
        f"- {CAT_CN.get(p.get('category', ''), '')}「{p.get('name', '')}」成分：{p.get('ingredients', '')}"
        for p in products
    )

    # Detect category intent for better LLM guidance
    cats_in_results = set(p.get("category", "") for p in products)
    is_food_only = "toy" not in cats_in_results

    ctx = engine._state_context(state)
    cat_hint = ""
    if is_food_only and any(w in query for w in ["零食", "吃的", "点心", "喝的", "饮品"]):
        cat_hint = f"顾客问{query}——这是食品类的需求。只介绍找到的食品即可，不要提香囊或其他品类。"
    elif not products:
        cat_hint = f"顾客问{query}——店里目前没有完全匹配的产品。请温和告知，建议先了解体质再做推荐。"

    instruction = (
        f"顾客搜索「{query}」，找到：\n\n{product_list}\n\n"
        f"{cat_hint}"
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
            product_svc = ProductService(db)
            rec_engine = RecommendEngine(product_svc, screening_result=state.get("screening_result", ""))
            const_type = state.get("constitution_type")
            recommendation = rec_engine.recommend(
                state.get("constitution_raw", "{}"),
                state.get("scene_raw", ""),
                constitution_type=const_type,
            )
            if recommendation and recommendation.get("bundle"):
                try:
                    result["message"] = _describe_recommendation(engine, state, recommendation)
                except Exception:
                    pass
    elif intent == "show_catalog":
        product_svc = ProductService(db)
        hot_products = product_svc.get_hot_products()
        constitution_catalog = product_svc.get_constitution_catalog()
        catalog = {
            "hot_products": hot_products,
            "constitution_catalog": constitution_catalog,
            "youzan_url": "https://shop187173170.m.youzan.com/v2/feature/7E6JIPDsLP",
            "youzan_qr": "/static/youzan-qr.jpg",
        }

    # Existing stage-based routing
    if result.get("stage") == Stage.RECOMMEND and not recommendation:
        product_svc = ProductService(db)
        rec_engine = RecommendEngine(product_svc, client=engine.client, screening_result=state.get("screening_result", ""))
        const_type = result.get("constitution_type") or state.get("constitution_type")
        const_raw = result.get("constitution_raw") or state.get("constitution_raw", "{}")
        recommendation = rec_engine.recommend(
            const_raw,
            result.get("scene_raw", "") or state.get("scene_raw", ""),
            constitution_type=const_type,
        )
        if recommendation.get("fixed_bundle") or recommendation.get("llm_recommendations"):
            try:
                if recommendation.get("no_match"):
                    result["message"] = _describe_fallback(engine, state, recommendation)
                else:
                    result["message"] = _describe_recommendation(engine, state, recommendation)
            except Exception:
                pass
    elif result.get("stage") == Stage.CATALOG and not catalog:
        product_svc = ProductService(db)
        catalog = product_svc.get_constitution_catalog()

    # Fix quick_replies and stage when recommendation or catalog content is shown
    if recommendation:
        result["quick_replies"] = ["推荐更多产品", "重新了解体质", "看看产品目录"]
        result["stage"] = Stage.RECOMMEND
    elif catalog:
        result["quick_replies"] = ["继续了解体质", "看看产品目录"]
        result["stage"] = Stage.CATALOG

    new_state = {**state, **result}
    if recommendation:
        new_state["recommendation"] = recommendation
    if catalog:
        new_state["catalog"] = catalog
    _session_store[state_key] = new_state

    # ── Persist conversation to DB ──────────────────────────────────────────
    now_iso = datetime.now().isoformat()
    conv_id = state.get("_conv_id")
    customer_id = state.get("_customer_id")

    # Build message history entry for this turn
    turn_entries = []
    if message:
        turn_entries.append({"role": "user", "content": message, "timestamp": now_iso})
    bot_msg = result.get("message", "")
    if bot_msg:
        entry = {"role": "assistant", "content": bot_msg, "timestamp": now_iso}
        qr = result.get("quick_replies")
        if qr:
            entry["quick_replies"] = qr
        turn_entries.append(entry)

    if conv_id:
        conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    else:
        conv = None

    if conv:
        # Update existing conversation
        prev_history = json.loads(conv.messages_history or "[]")
        new_history = prev_history + turn_entries
        conv.messages_history = json.dumps(new_history, ensure_ascii=False)

        prev_stages = json.loads(conv.stage_history or "[]")
        current_stage = new_state.get("stage", "")
        if current_stage and (not prev_stages or prev_stages[-1] != current_stage):
            prev_stages.append(current_stage)
            conv.stage_history = json.dumps(prev_stages, ensure_ascii=False)

        conv.stage = current_stage or conv.stage
        conv.screening_result = new_state.get("screening_result") or conv.screening_result
        if new_state.get("constitution_raw"):
            conv.constitution_raw = new_state["constitution_raw"]
        if new_state.get("scene_raw"):
            conv.scene_input = new_state["scene_raw"]
        # P1: save locked constitution type
        if new_state.get("constitution_type") and not conv.constitution_type:
            conv.constitution_type = new_state["constitution_type"]
            signals = new_state.get("constitution_signals", "{}")
            try:
                sigs = json.loads(signals) if isinstance(signals, str) else signals
                if sigs and conv.constitution_type in sigs:
                    conv.constitution_confidence = int(sigs[conv.constitution_type] * 100)
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
    else:
        # Create new conversation
        if not customer_id:
            customer = Customer(nickname="匿名顾客")
            db.add(customer)
            db.flush()
            customer_id = customer.id
            new_state["_customer_id"] = customer_id
            _session_store[state_key] = new_state

        stage_list = [new_state.get("stage", "greeting")]
        conv = Conversation(
            customer_id=customer_id,
            stage=new_state.get("stage", "greeting"),
            messages=message[:200] if message else "",
            messages_history=json.dumps(turn_entries, ensure_ascii=False),
            stage_history=json.dumps(stage_list, ensure_ascii=False),
            screening_result=new_state.get("screening_result", ""),
            constitution_raw=new_state.get("constitution_raw", "{}"),
            scene_input=new_state.get("scene_raw", ""),
            channel=req.channel or state.get("_channel", ""),
        )
        db.add(conv)
        db.flush()
        new_state["_conv_id"] = conv.id
        _session_store[state_key] = new_state

    # Update channel if provided
    if req.channel and conv and not conv.channel:
        conv.channel = req.channel

    db.commit()

    return {
        "message": result.get("message", ""),
        "stage": result.get("stage", "greeting"),
        "quick_replies": result.get("quick_replies"),
        "recommendation": recommendation,
        "catalog": catalog,
        "screening_result": new_state.get("screening_result"),
        "constitution_phase": new_state.get("constitution_phase"),
        "constitution_type": new_state.get("constitution_type"),
        "constitution_candidates": new_state.get("constitution_candidates"),
        "scene_from_constitution": new_state.get("scene_from_constitution"),
        "intent": result.get("intent"),
    }


@router.post("/reset")
def reset_session(req: ResetRequest):
    state_key = f"chat:{req.session_id}"
    _session_store.pop(state_key, None)
    return {"status": "ok"}
