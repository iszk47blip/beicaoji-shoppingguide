# backend/app/services/dialogue_engine.py
import json
from enum import Enum
from anthropic import Anthropic
from app.config import settings
from app.services.prompts import SYSTEM_PROMPT, WELCOME_MESSAGE, CONSTITUTION_QUESTIONS


class Stage(str, Enum):
    GREETING = "greeting"
    SCREENING = "screening"
    INFO_COLLECT = "info_collect"
    CONSTITUTION = "constitution"
    SCENE = "scene"
    RECOMMEND = "recommend"
    DONE = "done"


class DialogueEngine:
    def __init__(self):
        self.client = Anthropic(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

    # ------------------------------------------------------------------
    # LLM helpers
    # ------------------------------------------------------------------

    def _chat(self, instruction: str, context: str = "") -> str:
        messages = []
        if context:
            messages.append({"role": "user", "content": context})
        messages.append({"role": "user", "content": instruction})
        resp = self.client.messages.create(
            model=settings.llm_model,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        for block in resp.content:
            if hasattr(block, "text"):
                return block.text.strip()
        return ""

    def _chat_json(self, instruction: str, context: str = "") -> dict:
        text = self._chat(
            instruction + "\n\n只输出一行合法的JSON，不要markdown代码块，不要额外文字。",
            context
        )
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"message": text or "好的，请继续说。"}

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------

    def _state_context(self, state: dict) -> str:
        parts = []
        if state.get("customer_name"):
            parts.append(f"顾客名字: {state['customer_name']}")
        if state.get("screening_result"):
            parts.append(f"筛查结果: {state['screening_result']}")
        raw = state.get("constitution_raw", "{}")
        answers = json.loads(raw) if isinstance(raw, str) else raw
        if answers:
            answered = []
            for q in CONSTITUTION_QUESTIONS:
                if q["field"] in answers:
                    answered.append(f"{q['topic']}: {answers[q['field']]}")
            if answered:
                parts.append("已收集的体质信息:\n" + "\n".join(f"  - {a}" for a in answered))
        if state.get("scene_raw"):
            parts.append(f"顾客提到的生活困扰: {state['scene_raw']}")
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_bot_message(self, state: dict) -> dict:
        """Generate the bot's message when entering a new stage."""
        stage = state.get("stage", Stage.GREETING)
        if stage == Stage.GREETING:
            return {"message": WELCOME_MESSAGE, "stage": Stage.GREETING}
        elif stage == Stage.SCREENING:
            return self._screening_ask(state)
        elif stage == Stage.CONSTITUTION:
            return self._constitution_ask(state)
        elif stage == Stage.SCENE:
            return self._scene_ask(state)
        return {"message": "有什么我可以帮你的？", "stage": stage}

    def process_user_message(self, state: dict, user_input: str) -> dict:
        """Process user input and advance the conversation."""
        stage = state.get("stage", Stage.GREETING)
        user_input = user_input.strip()

        if stage == Stage.GREETING:
            return self._handle_greeting(state, user_input)
        elif stage == Stage.SCREENING:
            return self._handle_screening(state, user_input)
        elif stage == Stage.INFO_COLLECT:
            return self._handle_info_collect(state, user_input)
        elif stage == Stage.CONSTITUTION:
            return self._handle_constitution(state, user_input)
        elif stage == Stage.SCENE:
            return self._handle_scene(state, user_input)

        # Fallback
        ctx = self._state_context(state)
        msg = self._chat(
            f"顾客说：「{user_input}」。请自然回应，引导回到主流程。",
            ctx
        )
        return {"message": msg, "stage": stage}

    # ------------------------------------------------------------------
    # Stage: Greeting
    # ------------------------------------------------------------------

    def _handle_greeting(self, state: dict, user_input: str) -> dict:
        ctx = self._state_context(state)
        result = self._chat_json(
            f"顾客回应了你的欢迎：「{user_input}」\n\n"
            "根据顾客的话灵活回应，但无论什么情况都必须带出安全筛查（怀孕/备孕/哺乳/重大疾病/处方药）：\n"
            "- 顾客愿意继续 → 简短过渡后问筛查\n"
            "- 顾客问有什么产品 → 简短介绍品类（1句话），然后自然过渡：在帮你挑之前，先简单了解一下你的情况 + 问筛查\n"
            "- 顾客直接说困扰 → 表达理解，然后说为了更准确地帮你，先简单了解几个安全方面 + 问筛查\n"
            "- 顾客只是打招呼 → 简短回应后问筛查\n\n"
            "返回JSON: {\"message\": \"...\"}",
            ctx
        )
        result["stage"] = Stage.SCREENING
        return result

    # ------------------------------------------------------------------
    # Stage: Screening
    # ------------------------------------------------------------------

    def _screening_ask(self, state: dict) -> dict:
        msg = self._chat(
            "你需要对顾客做一个安全筛查。请自然地问他是否属于以下情况："
            "怀孕或备孕中、正在哺乳期、有确诊的重大疾病、正在服用处方药。"
            "语气温和，说明这关系到产品安全。"
        )
        return {"message": msg, "stage": Stage.SCREENING}

    def _handle_screening(self, state: dict, user_input: str) -> dict:
        ctx = self._state_context(state)
        result = self._chat_json(
            f"顾客对安全筛查的回应是：「{user_input}」\n\n"
            "首先判断顾客属于哪种情况：\n"
            "- 提到怀孕、备孕、哺乳、肿瘤、癌症、严重肝肾疾病 → screening_result = \"blocked\"\n"
            "- 提到处方药但没有上述情况 → screening_result = \"downgraded\"\n"
            "- 表示都没有或选E → screening_result = \"cleared\"\n"
            "- 顾客明确表示不想做筛查、想跳过 → screening_result = \"skipped\"\n\n"
            "然后生成回复：\n"
            "- cleared: 简短过渡，问顾客怎么称呼\n"
            "- blocked/downgraded: 温和建议咨询医生\n"
            "- skipped: 理解顾客，不再追问筛查，但温和提醒一句安全注意事项，然后直接进入体质了解\n\n"
            "返回JSON: {\"message\": \"...\", \"screening_result\": \"...\", "
            "\"stage\": \"info_collect|constitution|done\"}",
            ctx
        )
        screening_result = result.get("screening_result", "cleared")
        response = {"message": result.get("message", ""), "screening_result": screening_result}

        if screening_result == "blocked":
            response["stage"] = Stage.DONE
        elif screening_result == "downgraded":
            response["stage"] = Stage.DONE
        elif screening_result == "skipped":
            response["stage"] = Stage.CONSTITUTION
            response["constitution_index"] = 0
            response["constitution_raw"] = "{}"
        else:
            response["stage"] = Stage.INFO_COLLECT
        return response

    # ------------------------------------------------------------------
    # Stage: Info Collect
    # ------------------------------------------------------------------

    def _handle_info_collect(self, state: dict, user_input: str) -> dict:
        ctx = self._state_context(state)
        q = CONSTITUTION_QUESTIONS[0]

        result = self._chat_json(
            f"你刚才问了顾客怎么称呼，顾客说：「{user_input}」\n\n"
            "请判断顾客的意图并灵活回应：\n"
            "- 如果顾客说了名字/称呼 → 用名字打招呼，然后自然过渡到第一个体质问题\n"
            "- 如果顾客不想说名字或想跳过 → 无所谓，直接进入体质了解\n"
            "- 如果顾客问产品、闲聊 → 简短回应后引导到体质了解\n\n"
            f"如果要进入体质环节，请自然地提出第一个问题：「{q['question']}」"
            f"（选项: {', '.join(q['options'])}）\n\n"
            "返回JSON: {\"message\": \"...\", \"customer_name\": \"名字或空\", "
            "\"stage\": \"constitution|greeting\"}",
            ctx
        )

        name = result.get("customer_name", "").strip() or user_input.strip()
        response = {
            "message": result.get("message", f"好的，那我们开始了解一下你的身体状态。{q['question']}"),
            "stage": Stage.CONSTITUTION,
            "constitution_index": 0,
            "constitution_raw": "{}",
            "customer_name": name,
        }
        return response

    # ------------------------------------------------------------------
    # Stage: Constitution
    # ------------------------------------------------------------------

    def _constitution_ask(self, state: dict) -> dict:
        idx = state.get("constitution_index", 0)
        if idx >= len(CONSTITUTION_QUESTIONS):
            return self._transition_to_scene(state)
        q = CONSTITUTION_QUESTIONS[idx]
        ctx = self._state_context(state)
        msg = self._chat(
            f"请自然地提出这个问题：「{q['question']}」\n"
            f"选项供顾客参考：{', '.join(q['options'])}",
            ctx
        )
        return {"message": msg, "stage": Stage.CONSTITUTION, "question_index": idx}

    def _handle_constitution(self, state: dict, user_input: str) -> dict:
        idx = state.get("constitution_index", 0)
        raw = json.loads(state.get("constitution_raw", "{}"))
        q = CONSTITUTION_QUESTIONS[idx] if idx < len(CONSTITUTION_QUESTIONS) else None

        if q is None:
            return self._transition_to_scene(state)

        is_last = idx + 1 >= len(CONSTITUTION_QUESTIONS)

        if is_last:
            instruction = (
                f"顾客被问到：「{q['question']}」选项：{json.dumps(q['options'], ensure_ascii=False)}\n"
                f"顾客回答：「{user_input}」\n\n"
                "请做两件事：\n"
                "1. 判断顾客的选择最接近哪个选项原文（如果顾客跳过，填'未回答'）\n"
                "2. 简短温暖地回应，然后过渡到询问生活困扰的环节\n\n"
                "如果顾客说想跳过或不想回答 → 直接进入生活困扰环节\n\n"
                "返回JSON: {\"message\": \"...\", \"value\": \"最接近的选项原文或未回答\"}"
            )
        else:
            next_q = CONSTITUTION_QUESTIONS[idx + 1]
            instruction = (
                f"顾客被问到：「{q['question']}」选项：{json.dumps(q['options'], ensure_ascii=False)}\n"
                f"顾客回答：「{user_input}」\n\n"
                "请灵活处理：\n"
                "1. 判断顾客的选择最接近哪个选项原文（如果跳过或无关，填'未回答'）\n"
                "2. 简短温暖地回应\n"
                "3. 如果顾客想跳过当前问题 → 尊重，进下一个\n"
                "4. 如果顾客想跳过所有体质问题 → 直接进入生活困扰环节\n\n"
                f"下一个问题：「{next_q['question']}」（选项: {', '.join(next_q['options'])}）\n\n"
                "返回JSON: {\"message\": \"...\", \"value\": \"...\", "
                "\"stage\": \"constitution|scene\"}"
            )

        ctx = self._state_context(state)
        result = self._chat_json(instruction, ctx)

        extracted_value = result.get("value", user_input)
        if extracted_value and extracted_value != "未回答":
            raw[q["field"]] = extracted_value
        idx += 1

        # Allow LLM to skip to scene
        next_stage = result.get("stage", Stage.SCENE if is_last else Stage.CONSTITUTION)

        response = {
            "message": result.get("message", "好的，了解了。"),
            "constitution_raw": json.dumps(raw, ensure_ascii=False),
            "constitution_index": idx,
            "stage": Stage.SCENE if (is_last or next_stage == Stage.SCENE) else Stage.CONSTITUTION,
        }
        return response

    def _transition_to_scene(self, state: dict) -> dict:
        ctx = self._state_context(state)
        msg = self._chat(
            "体质了解环节结束了。请自然地告诉顾客你已经了解了大致情况，"
            "接下来想了解他最近的生活困扰，比如睡眠、消化、疲劳、皮肤等。",
            ctx
        )
        return {"message": msg, "stage": Stage.SCENE}

    # ------------------------------------------------------------------
    # Stage: Scene
    # ------------------------------------------------------------------

    def _scene_ask(self, state: dict) -> dict:
        ctx = self._state_context(state)
        msg = self._chat(
            "请询问顾客最近有没有什么特别困扰他的，比如睡不好、消化差、容易疲劳、"
            "皮肤状态不好、想调理身体等等。",
            ctx
        )
        return {"message": msg, "stage": Stage.SCENE}

    def _handle_scene(self, state: dict, user_input: str) -> dict:
        scene_raw = state.get("scene_raw", "")
        followup_done = state.get("scene_followup_done", False)
        ctx = self._state_context(state)

        if not scene_raw:
            result = self._chat_json(
                f"顾客描述了最近的生活困扰：「{user_input}」\n\n"
                "请灵活处理：\n"
                "- 如果顾客说了具体困扰 → 表示理解共情，追问一个更具体的细节\n"
                "- 如果顾客说没有特别困扰 → 没关系，直接进入推荐环节\n"
                "- 如果顾客跳过或闲聊 → 简短回应后进入推荐\n\n"
                "返回JSON: {\"message\": \"...\", \"stage\": \"scene|recommend\"}",
                ctx
            )
            next_stage = result.get("stage", Stage.SCENE)
            response = {"message": result.get("message", ""), "scene_raw": user_input}
            if next_stage == Stage.RECOMMEND:
                response["stage"] = Stage.RECOMMEND
                response["scene_followup_done"] = True
            else:
                response["stage"] = Stage.SCENE
            return response

        elif not followup_done:
            combined_scene = f"{scene_raw}；{user_input}"
            result = self._chat_json(
                f"顾客补充了更多细节：「{user_input}」（之前说的是「{scene_raw}」）\n\n"
                "表示理解，然后告诉顾客已经收集了足够的信息，"
                "现在帮他做综合分析和推荐。\n\n"
                "返回JSON: {\"message\": \"...\"}",
                ctx
            )
            result["stage"] = Stage.RECOMMEND
            result["scene_raw"] = combined_scene
            result["scene_followup_done"] = True
            return result

        else:
            result = self._chat_json(
                "请自然地告诉顾客，马上帮他分析推荐合适的产品。\n"
                "返回JSON: {\"message\": \"...\"}",
                ctx
            )
            result["stage"] = Stage.RECOMMEND
            return result
