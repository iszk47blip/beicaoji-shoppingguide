# backend/tests/test_dialogue_engine.py
import json
from unittest.mock import patch
from app.services.dialogue_engine import DialogueEngine, Stage


def _mock_chat(self, instruction, context=""):
    """Simulate LLM text response."""
    return "你好！我是小焙，很高兴见到你。"


def _extract_user_input(instruction):
    """Extract the user's actual response from instruction text like '顾客说：「...」'."""
    if "「" in instruction and "」" in instruction:
        return instruction.split("「")[1].split("」")[0]
    return ""


def _mock_chat_json(self, instruction, context=""):
    """Simulate LLM JSON response — extract user input from instruction to decide."""
    msg = "好的，了解了。"
    user = _extract_user_input(instruction)

    if "screening_result" in instruction:
        if any(w in user for w in ["怀孕", "备孕", "哺乳", "肿瘤", "癌症", "A", "B", "C"]):
            return {"message": "感谢你的坦诚，建议先咨询医生。", "screening_result": "blocked"}
        elif "处方药" in user or "D" in user:
            return {"message": "你在服用什么药呢？", "screening_result": "downgraded"}
        else:
            return {"message": "好的，请问怎么称呼你？", "screening_result": "cleared"}

    if "value" in instruction and "最接近的选项" in instruction:
        # Constitution answer extraction
        return {"message": "嗯，了解了。下一个问题...", "value": "偏凉，冬天容易手脚冰凉"}

    if "value" in instruction and "最后一个体质" in instruction:
        return {
            "message": "好的，大致了解了。再聊聊你最近有什么困扰吧？",
            "value": "挺好的，基本没问题"
        }

    return {"message": msg}


class TestGreeting:
    @patch.object(DialogueEngine, '_chat', _mock_chat)
    def test_greeting_message(self):
        engine = DialogueEngine()
        result = engine.get_bot_message({"stage": Stage.GREETING})
        assert len(result["message"]) > 0
        assert result["stage"] == Stage.GREETING

    @patch.object(DialogueEngine, '_chat_json', _mock_chat_json)
    def test_greeting_transition_to_screening(self):
        engine = DialogueEngine()
        result = engine.process_user_message({"stage": Stage.GREETING}, "你好")
        assert result["stage"] == Stage.SCREENING
        assert len(result["message"]) > 0


class TestScreening:
    @patch.object(DialogueEngine, '_chat_json', _mock_chat_json)
    def test_screening_cleared(self):
        engine = DialogueEngine()
        result = engine.process_user_message({"stage": Stage.SCREENING}, "E 都没有")
        assert result["stage"] == Stage.INFO_COLLECT
        assert result["screening_result"] == "cleared"

    @patch.object(DialogueEngine, '_chat_json', _mock_chat_json)
    def test_screening_blocked(self):
        engine = DialogueEngine()
        result = engine.process_user_message({"stage": Stage.SCREENING}, "A 怀孕")
        assert result["screening_result"] == "blocked"
        assert result["stage"] == Stage.DONE


class TestInfoCollect:
    @patch.object(DialogueEngine, '_chat_json', _mock_chat_json)
    def test_info_collect_transitions_to_constitution(self):
        engine = DialogueEngine()
        result = engine.process_user_message({"stage": Stage.INFO_COLLECT}, "小明")
        assert result["stage"] == Stage.CONSTITUTION
        assert result["constitution_index"] == 0
        assert result["customer_name"] == "小明"
        assert result["constitution_raw"] == "{}"


class TestConstitution:
    @patch.object(DialogueEngine, '_chat_json', _mock_chat_json)
    def test_constitution_stores_answer(self):
        engine = DialogueEngine()
        state = {"stage": Stage.CONSTITUTION, "constitution_index": 0, "constitution_raw": "{}"}
        result = engine.process_user_message(state, "偏凉，冬天手脚冰冷")
        assert result["stage"] == Stage.CONSTITUTION
        assert result["constitution_index"] == 1
        raw = json.loads(result["constitution_raw"])
        assert "temperature_tendency" in raw

    @patch.object(DialogueEngine, '_chat_json', _mock_chat_json)
    def test_constitution_last_question_transitions_to_scene(self):
        engine = DialogueEngine()
        state = {
            "stage": Stage.CONSTITUTION,
            "constitution_index": 5,
            "constitution_raw": '{"temperature_tendency":"偏凉","heat_signs":"偶尔"}',
        }
        result = engine.process_user_message(state, "挺好的")
        assert result["stage"] == Stage.SCENE
        assert result["constitution_index"] == 6


class TestScene:
    @patch.object(DialogueEngine, '_chat_json', _mock_chat_json)
    def test_scene_first_input(self):
        engine = DialogueEngine()
        result = engine.process_user_message({"stage": Stage.SCENE}, "最近睡不好")
        assert result["stage"] == Stage.SCENE
        assert result["scene_raw"] == "最近睡不好"

    @patch.object(DialogueEngine, '_chat_json', _mock_chat_json)
    def test_scene_followup_transitions_to_recommend(self):
        engine = DialogueEngine()
        state = {"stage": Stage.SCENE, "scene_raw": "睡不好"}
        result = engine.process_user_message(state, "入睡困难")
        assert result["stage"] == Stage.RECOMMEND
        assert result["scene_followup_done"] is True
