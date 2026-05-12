# backend/tests/test_dialogue_engine.py
import json
from app.services.dialogue_engine import DialogueEngine, Stage

def test_greeting():
    engine = DialogueEngine()
    result = engine.get_bot_message({"stage": Stage.GREETING})
    assert "焙草集" in result["message"]
    assert result["stage"] == Stage.GREETING

def test_screening_cleared():
    engine = DialogueEngine()
    state = {"stage": Stage.SCREENING}
    result = engine.process_user_message(state, "E")
    assert result["stage"] == Stage.INFO_COLLECT
    assert result["screening_result"] == "cleared"

def test_screening_blocked_pregnancy():
    engine = DialogueEngine()
    state = {"stage": Stage.SCREENING}
    result = engine.process_user_message(state, "A 怀孕")
    assert result["screening_result"] == "blocked"

def test_constitution_flow():
    engine = DialogueEngine()
    state = {"stage": Stage.CONSTITUTION, "constitution_index": 0, "constitution_raw": "{}"}
    result = engine.process_user_message(state, "偏凉")
    assert result["stage"] == Stage.CONSTITUTION
    raw = json.loads(result["constitution_raw"])
    assert raw.get("temperature_tendency") == "偏凉"
    assert result.get("constitution_index") == 1