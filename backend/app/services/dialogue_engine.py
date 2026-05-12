# backend/app/services/dialogue_engine.py
import json
from enum import Enum
from openai import OpenAI
from app.config import settings
from app.services.prompts import (
    SYSTEM_PROMPT, SCREENING_PROMPT, CONSTITUTION_QUESTIONS,
    SCENE_QUESTION, SCENE_FOLLOWUP,
    SCREENING_BLOCKED_MSG, SCREENING_DRUG_MSG,
)

class Stage(str, Enum):
    GREETING = "greeting"
    SCREENING = "screening"
    SCREENING_RESULT = "screening_result"
    INFO_COLLECT = "info_collect"
    CONSTITUTION = "constitution"
    SCENE = "scene"
    RECOMMEND = "recommend"
    REPORT = "report"
    DONE = "done"

class DialogueEngine:
    def __init__(self):
        self.client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)

    def get_bot_message(self, conversation_state: dict) -> dict:
        stage = conversation_state.get("stage", Stage.GREETING)
        constitution_answers = json.loads(conversation_state.get("constitution_raw", "{}"))

        if stage == Stage.GREETING:
            return self._greeting()
        elif stage == Stage.SCREENING:
            return self._screening()
        elif stage == Stage.CONSTITUTION:
            idx = conversation_state.get("constitution_index", 0)
            if idx < len(CONSTITUTION_QUESTIONS):
                q = CONSTITUTION_QUESTIONS[idx]
                options_text = "\n".join(f"  · {o}" for o in q["options"])
                return {"message": f"{q['question']}\n\n{options_text}", "stage": stage, "question_index": idx}
            else:
                return {"message": SCENE_QUESTION, "stage": Stage.SCENE}
        elif stage == Stage.SCENE:
            last_answer = conversation_state.get("scene_raw", "")
            if last_answer and not conversation_state.get("scene_followup_done"):
                return {"message": self._scene_followup(last_answer), "stage": stage}
            return {"message": "好的，我已经了解了你的情况，让我为你分析一下……", "stage": Stage.RECOMMEND}
        return {"message": "有什么我可以帮你的？", "stage": stage}

    def process_user_message(self, state: dict, user_input: str) -> dict:
        user_input = user_input.strip()
        if state.get("stage") == Stage.GREETING:
            return self._handle_greeting(state, user_input)
        elif state.get("stage") == Stage.SCREENING:
            return self._handle_screening(state, user_input)
        elif state.get("stage") == Stage.CONSTITUTION:
            return self._handle_constitution(state, user_input)
        elif state.get("stage") == Stage.SCENE:
            return self._handle_scene(state, user_input)
        return self.get_bot_message(state)

    def _handle_greeting(self, state, user_input):
        return {"message": SCREENING_PROMPT, "stage": Stage.SCREENING}

    def _greeting(self):
        return {
            "message": "你好！我是焙草集的健康顾问 🌿\n\n"
                       "我可以帮你了解自己的身体状态，推荐适合你的药食同源调理产品。\n"
                       "整个过程大约1分钟，先简单了解一下你的情况。准备好了吗？",
            "stage": Stage.GREETING,
        }

    def _screening(self):
        return {"message": SCREENING_PROMPT, "stage": Stage.SCREENING}

    def _handle_screening(self, state, user_input):
        lowered = user_input.lower()
        blocked_keywords = ["a", "b", "c", "怀孕", "备孕", "哺乳", "肿瘤", "癌症"]
        drug_keywords = ["d", "处方药"]
        is_blocked = any(k in lowered for k in blocked_keywords)
        is_drug = any(k in lowered for k in drug_keywords)
        if is_blocked:
            return {"message": SCREENING_BLOCKED_MSG, "stage": Stage.SCREENING_RESULT, "screening_result": "blocked"}
        elif is_drug:
            return {"message": SCREENING_DRUG_MSG, "stage": Stage.SCREENING_RESULT, "screening_result": "downgraded"}
        else:
            return {"message": "好的，那我们继续。方便告诉我怎么称呼你吗？", "stage": Stage.INFO_COLLECT, "screening_result": "cleared"}

    def _handle_constitution(self, state, user_input):
        idx = state.get("constitution_index", 0)
        raw = json.loads(state.get("constitution_raw", "{}"))
        q = CONSTITUTION_QUESTIONS[idx]
        raw[q["field"]] = user_input
        idx += 1
        if idx >= len(CONSTITUTION_QUESTIONS):
            return {"message": SCENE_QUESTION, "stage": Stage.SCENE, "constitution_raw": json.dumps(raw, ensure_ascii=False), "constitution_index": idx}
        else:
            next_q = CONSTITUTION_QUESTIONS[idx]
            options_text = "\n".join(f"  · {o}" for o in next_q["options"])
            return {"message": f"{next_q['question']}\n\n{options_text}", "stage": Stage.CONSTITUTION, "constitution_raw": json.dumps(raw, ensure_ascii=False), "constitution_index": idx}

    def _handle_scene(self, state, user_input):
        if not state.get("scene_raw"):
            return {"message": "好的，我已经了解你的情况了，现在帮你分析适合你的产品……", "stage": Stage.RECOMMEND, "scene_raw": user_input}
        return {"message": "好的，我已经了解你的情况了，现在帮你分析适合你的产品……", "stage": Stage.RECOMMEND, "scene_raw": state["scene_raw"], "scene_followup_done": True}

    def _scene_followup(self, scene_input):
        lowered = scene_input
        if "睡" in lowered:
            return "是入睡困难，还是半夜容易醒、醒了就睡不着？"
        elif "消化" in lowered or "肠胃" in lowered or "胃" in lowered:
            return "主要是饭后胀气、反酸，还是大便不太规律？"
        elif "累" in lowered or "疲劳" in lowered:
            return "是一整天都累，还是下午特别明显？"
        return "能再具体描述一下吗？"