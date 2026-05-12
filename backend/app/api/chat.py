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


class ResetRequest(BaseModel):
    session_id: str


@router.post("/send")
def send_message(
    session_id: str = Body(...),
    message: str = Body(""),
    db=Depends(get_db)
):
    state_key = f"chat:{session_id}"
    state = _session_store.get(state_key) or {"stage": "greeting"}

    if not message:
        result = engine.get_bot_message(state)
    else:
        result = engine.process_user_message(state, message)

    recommendation = None
    if result.get("stage") == "recommend":
        product_svc = ProductService(db)
        rec_engine = RecommendEngine(product_svc)
        recommendation = rec_engine.recommend(
            state.get("constitution_raw", "{}"),
            result.get("scene_raw", "")
        )

    new_state = {**state, **result}
    _session_store[state_key] = new_state

    return {
        "message": result.get("message", ""),
        "stage": result.get("stage", "greeting"),
        "quick_replies": result.get("quick_replies"),
        "recommendation": recommendation,
    }


@router.post("/reset")
def reset_session(req: ResetRequest):
    state_key = f"chat:{req.session_id}"
    _session_store.pop(state_key, None)
    return {"status": "ok"}
