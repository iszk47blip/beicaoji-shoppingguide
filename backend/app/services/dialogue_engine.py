# backend/app/services/dialogue_engine.py
import json
import re
from enum import Enum
from anthropic import Anthropic
from app.config import settings
from app.services.prompts import (
    SYSTEM_PROMPT, WELCOME_MESSAGE,
    CONSTITUTION_FIELDS, ADAPTIVE_FIELD_ORDER,
    CONSTITUTION_EXTRACTION_SYSTEM, CONSTITUTION_EXTRACTION_USER,
    CONSTITUTION_ENTRY_REPLIES,
)


class Stage(str, Enum):
    GREETING = "greeting"
    SCREENING = "screening"
    INFO_COLLECT = "info_collect"
    CONSTITUTION = "constitution"
    SCENE = "scene"
    RECOMMEND = "recommend"
    CATALOG = "catalog"
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
            max_tokens=1024,
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
            pass
        # Try to extract message field from truncated JSON
        m = re.search(r'"message"\s*:\s*"([^"]+)', text)
        if m:
            return {"message": m.group(1)}
        # If text looks like JSON but couldn't parse, use it as plain message
        if text.startswith("{") or text.startswith('"'):
            text = text.strip('{}"').strip()
        return {"message": text or "好的，请继续说。"}

    def _extract_signals(self, user_input: str) -> dict:
        """Extract 5 constitution signal fields from free-text user input."""
        prompt = CONSTITUTION_EXTRACTION_USER.replace("{user_input}", user_input)
        resp = self.client.messages.create(
            model=settings.llm_model,
            max_tokens=512,
            system=CONSTITUTION_EXTRACTION_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        text = ""
        for block in resp.content:
            if hasattr(block, "text"):
                text = block.text.strip()
                break
        if not text:
            return {}
        text = text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

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
            for field, info in CONSTITUTION_FIELDS.items():
                if field in answers and answers[field]:
                    answered.append(f"{info['topic']}: {answers[field]}")
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
            return {
                "message": WELCOME_MESSAGE, "stage": Stage.GREETING,
                "quick_replies": ["帮我看看体质", "你都有什么产品？"]
            }
        elif stage == Stage.SCREENING:
            return self._screening_ask(state)
        elif stage == Stage.CONSTITUTION:
            return self._constitution_ask(state)
        elif stage == Stage.SCENE:
            return self._scene_ask(state)
        elif stage == Stage.RECOMMEND:
            return self._recommend_reenter(state)
        elif stage == Stage.CATALOG:
            return self._catalog_reenter(state)
        elif stage == Stage.DONE:
            return {"message": "欢迎随时回来。有什么可以帮你的？", "stage": Stage.GREETING,
                    "quick_replies": ["帮我看看体质", "你都有什么产品？"]}
        return {"message": "有什么我可以帮你的？", "stage": stage}

    def _recommend_reenter(self, state: dict) -> dict:
        ctx = self._state_context(state)
        msg = self._chat(
            "顾客回到推荐页。自然地问他还想了解什么，要不要重新看体质或换个困扰。",
            ctx
        )
        return {"message": msg, "stage": Stage.RECOMMEND,
                "quick_replies": ["推荐更多产品", "重新了解体质", "看看产品目录"]}

    def _catalog_reenter(self, state: dict) -> dict:
        ctx = self._state_context(state)
        msg = self._chat(
            "顾客看产品目录。介绍四大品类：饼干、面包、茶、香囊。问想看哪类。",
            ctx
        )
        return {"message": msg, "stage": Stage.CATALOG,
                "quick_replies": ["饼干", "面包", "茶", "香囊", "帮我看看体质"]}

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
        elif stage == Stage.RECOMMEND:
            return self._handle_recommend(state, user_input)
        elif stage == Stage.CATALOG:
            return self._handle_catalog(state, user_input)
        elif stage == Stage.DONE:
            return self._handle_done(state, user_input)

        ctx = self._state_context(state)
        result = self._chat_json(
            f"顾客说：「{user_input}」。请自然回应，引导回到主流程。\n\n"
            "判断顾客意图：\n"
            "- 顾客想找具体产品、想让你推荐 → intent: search_product\n"
            "- 顾客想看所有产品目录 → intent: show_catalog\n"
            "- 其他 → intent: continue_flow\n\n"
            "返回JSON: {\"message\": \"...\", \"intent\": \"search_product|show_catalog|continue_flow\"}",
            ctx
        )
        return {"message": result.get("message", msg), "stage": stage,
                "intent": result.get("intent", "continue_flow")}

    # ------------------------------------------------------------------
    # Stage: Greeting
    # ------------------------------------------------------------------

    def _handle_greeting(self, state: dict, user_input: str) -> dict:
        # Quick product intent pre-check — only for clearly product-specific phrases
        product_phrases = ["有没有", "多少钱", "给我推", "我要买", "来一", "买一",
                           "推荐几个", "推荐一款", "推荐一下", "推几个"]
        if any(kw in user_input for kw in product_phrases):
            intent = self._detect_product_intent(state, user_input)
            if intent == "search_product" or intent == "show_catalog":
                return {"message": "", "stage": Stage.GREETING, "intent": intent}

        ctx = self._state_context(state)
        result = self._chat_json(
            f"顾客说：「{user_input}」\n\n"
            "你是门店店员，根据顾客的话灵活回应：\n"
            "- 问产品/找推荐 → 介绍产品后引导回体质了解，stage: greeting\n"
            "- 不想做体质/想看所有产品 → 介绍四大品类，stage: catalog\n"
            "- 说了身体困扰 → 表达理解后做安全筛查，stage: screening\n"
            "- 愿意了解体质/打招呼 → 自然过渡到筛查，stage: screening\n\n"
            "意图：找具体产品→search_product；看所有产品→show_catalog；其他→continue_flow\n"
            "JSON: {\"message\":\"...\",\"stage\":\"screening|greeting|catalog\",\"intent\":\"search_product|show_catalog|continue_flow\"}",
            ctx
        )
        next_stage = result.get("stage", Stage.SCREENING)
        intent = result.get("intent", "continue_flow")
        result["stage"] = next_stage
        result["intent"] = intent
        if next_stage == Stage.SCREENING:
            result["quick_replies"] = ["都没有", "在备孕或怀孕", "在哺乳期", "在吃处方药"]
        elif next_stage == Stage.GREETING:
            result["quick_replies"] = ["帮我看看体质", "饼干有哪些？", "有什么茶？"]
        elif next_stage == Stage.CATALOG:
            result["quick_replies"] = None
        return result

    # ------------------------------------------------------------------
    # Stage: Screening
    # ------------------------------------------------------------------

    def _screening_ask(self, state: dict) -> dict:
        msg = self._chat(
            "自然地询问顾客：是否怀孕/备孕、哺乳期、重大疾病、服用处方药。语气温和，说明是为了产品安全。"
        )
        return {
            "message": msg, "stage": Stage.SCREENING,
            "quick_replies": ["都没有", "在备孕或怀孕", "在哺乳期", "在吃处方药"]
        }

    def _handle_screening(self, state: dict, user_input: str) -> dict:
        ctx = self._state_context(state)
        result = self._chat_json(
            f"顾客筛查回应：「{user_input}」\n"
            "判定：怀孕/备孕/哺乳/肿瘤/严重肝肾→blocked；处方药无上述→downgraded；都没有→cleared；想跳过→skipped\n"
            "回复：cleared→过渡到问称呼；blocked/downgraded→温和建议看医生；skipped→提醒安全后进入体质\n"
            "意图：search_product/show_catalog/continue_flow\n"
            "JSON: {\"message\":\"...\",\"screening_result\":\"...\",\"stage\":\"info_collect|constitution|done\",\"intent\":\"...\"}",
            ctx
        )
        screening_result = result.get("screening_result", "cleared")
        response = {"message": result.get("message", ""), "screening_result": screening_result,
                    "intent": result.get("intent", "continue_flow")}

        if screening_result == "blocked":
            response["stage"] = Stage.DONE
        elif screening_result == "downgraded":
            response["stage"] = Stage.DONE
        elif screening_result == "skipped":
            response["stage"] = Stage.CONSTITUTION
            response["constitution_extract_done"] = False
            response["constitution_questions_asked"] = 0
            response["constitution_raw"] = "{}"
            response["quick_replies"] = CONSTITUTION_ENTRY_REPLIES
        else:
            response["stage"] = Stage.INFO_COLLECT
        return response

    # ------------------------------------------------------------------
    # Stage: Info Collect
    # ------------------------------------------------------------------

    def _handle_info_collect(self, state: dict, user_input: str) -> dict:
        ctx = self._state_context(state)

        result = self._chat_json(
            f"顾客回应：「{user_input}」\n\n"
            "说了名字→用名字打招呼，然后自然地请他聊聊最近身体感觉怎么样，用开放式问题\n"
            "不想说名字→没关系，直接请他聊聊身体感受\n"
            "问产品/闲聊→简短回应后引导回体质\n\n"
            "铁律：不要提任何具体的体质问题（如手脚凉不凉、上不上火），不要列选项，不要用'第一个问题'这种字眼\n"
            "像朋友聊天一样，请他随便说说最近身体的感觉\n\n"
            "意图：search_product/show_catalog/continue_flow\n"
            "JSON: {\"message\":\"...\",\"customer_name\":\"名字或空\",\"stage\":\"constitution|greeting\",\"intent\":\"...\"}",
            ctx
        )

        name = result.get("customer_name", "").strip() or user_input.strip()
        response = {
            "message": result.get("message", "好的，那跟我说说你最近身体感觉怎么样吧？"),
            "stage": Stage.CONSTITUTION,
            "constitution_extract_done": False,
            "constitution_questions_asked": 0,
            "constitution_raw": "{}",
            "customer_name": name,
            "quick_replies": list(CONSTITUTION_ENTRY_REPLIES),
            "intent": result.get("intent", "continue_flow"),
        }
        return response

    # ------------------------------------------------------------------
    # Stage: Constitution (B+C hybrid: free-text extraction + adaptive QA)
    # ------------------------------------------------------------------

    def _constitution_ask(self, state: dict) -> dict:
        """Ask the free-text opening question for constitution extraction."""
        ctx = self._state_context(state)
        msg = self._chat(
            "请顾客聊聊最近身体感觉怎么样，有什么不舒服或在意的地方。不要列选项，让他用自己的话说。",
            ctx
        )
        return {
            "message": msg,
            "stage": Stage.CONSTITUTION,
            "quick_replies": CONSTITUTION_ENTRY_REPLIES,
        }

    def _handle_constitution(self, state: dict, user_input: str) -> dict:
        # In constitution, users saying these words are likely trying to escape
        product_keywords = ["有没有", "多少钱", "给我", "推给", "推荐", "我要",
                            "买", "不用", "算了", "直接", "就要", "只要", "来个"]
        looks_like_product = any(kw in user_input for kw in product_keywords)

        if looks_like_product:
            intent = self._detect_product_intent(state, user_input)
            if intent == "search_product" or intent == "show_catalog":
                return {"message": "", "stage": state.get("stage", Stage.CONSTITUTION),
                        "intent": intent}

        extract_done = state.get("constitution_extract_done", False)
        questions_asked = state.get("constitution_questions_asked", 0)
        ctx = self._state_context(state)

        if not extract_done:
            return self._handle_constitution_extract(state, user_input, ctx)
        else:
            return self._handle_constitution_adaptive(state, user_input, questions_asked, ctx)

    def _detect_product_intent(self, state: dict, user_input: str) -> str:
        """Quick LLM check: is the user asking for products instead of answering constitution?"""
        ctx = self._state_context(state)
        result = self._chat_json(
            f"顾客说：「{user_input}」\n\n"
            "只判断一件事：顾客是想找产品、要推荐、想看目录吗？\n"
            "- 明确要某种产品（比如'给我推荐XX'、'有没有XX'、'我就想喝XX'、'算了别问了直接推XX'）→ search_product\n"
            "- 想看所有产品目录 → show_catalog\n"
            "- 在回答体质问题、描述身体感觉、闲聊 → continue_flow\n\n"
            "返回JSON: {\"intent\": \"search_product|show_catalog|continue_flow\"}",
            ctx
        )
        return result.get("intent", "continue_flow")

    def _handle_constitution_extract(self, state: dict, user_input: str, ctx: str) -> dict:
        """Phase 1: extract signals from free-text, decide next step."""
        raw = json.loads(state.get("constitution_raw", "{}"))
        signals = self._extract_signals(user_input)

        if not signals:
            # Extraction failed — fall back to adaptive QA
            return self._ask_adaptive_question(raw, {}, 0, ctx, "好的，让我再了解一下～")

        # Count non-empty signals
        filled = {f: v for f, v in signals.items() if v}
        clear_count = len(filled)

        if clear_count >= 2:
            # Enough signals — confirm and transition to SCENE
            for f, v in filled.items():
                raw[f] = v
            response = {
                "constitution_raw": json.dumps(raw, ensure_ascii=False),
                "constitution_extract_done": True,
            }
            return self._transition_to_scene_from_extract(state, response, ctx)

        elif clear_count == 1:
            # One signal — ask one adaptive question
            for f, v in filled.items():
                raw[f] = v
            return self._ask_adaptive_question(
                raw, filled, 0, ctx,
                "了解了～再问你一个小问题"
            )

        else:
            # Zero signals — ask first adaptive question
            return self._ask_adaptive_question(
                raw, {}, 0, ctx,
                "好的～让我帮你看看。先问你一个小问题："
            )

    def _handle_constitution_adaptive(self, state: dict, user_input: str,
                                      questions_asked: int, ctx: str) -> dict:
        """Phase 2: process adaptive QA answer, decide whether to ask more or proceed."""
        raw = json.loads(state.get("constitution_raw", "{}"))
        known_signals = {f: v for f, v in raw.items() if v}

        # Ask LLM to map user answer to a specific field and value
        result = self._chat_json(
            f"顾客回答了一个体质相关问题：「{user_input}」\n\n"
            "请判断顾客的选择最接近哪个选项原文：\n"
            + "\n".join(
                f"- {info['topic']}({field}): {', '.join(info['options'])}"
                for field, info in CONSTITUTION_FIELDS.items()
                if field not in known_signals
            ) +
            "\n\n如果顾客跳过或含糊，填'未回答'。\n"
            "返回JSON: {\"field\": \"字段名或空\", \"value\": \"选项原文或未回答\"}",
            ctx
        )

        field = result.get("field", "")
        value = result.get("value", "")
        if field and value and value != "未回答":
            raw[field] = value
            known_signals[field] = value

        questions_asked += 1
        clear_count = len(known_signals)

        if clear_count >= 2 or questions_asked >= 2:
            # Enough signals or hit question limit — proceed to SCENE
            response = {
                "constitution_raw": json.dumps(raw, ensure_ascii=False),
                "constitution_extract_done": True,
                "constitution_questions_asked": questions_asked,
            }
            return self._transition_to_scene_from_extract(state, response, ctx)

        # Need one more question
        return self._ask_adaptive_question(
            raw, known_signals, questions_asked, ctx,
            "好的，最后一个问题～"
        )

    def _ask_adaptive_question(self, raw: dict, known_signals: dict,
                                questions_asked: int, ctx: str,
                                prefix: str) -> dict:
        """Ask the next adaptive question for the most discriminating missing field."""
        # Find first missing field in priority order
        missing_field = None
        for f in ADAPTIVE_FIELD_ORDER:
            if f not in known_signals:
                missing_field = f
                break

        if missing_field is None:
            # All fields filled — proceed
            response_state = {
                "constitution_raw": json.dumps(raw, ensure_ascii=False),
                "constitution_extract_done": True,
                "constitution_questions_asked": questions_asked,
            }
            return self._transition_to_scene_from_extract({}, response_state, ctx)

        info = CONSTITUTION_FIELDS[missing_field]
        # Let LLM generate a natural question for this field
        result = self._chat_json(
            f"你需要了解顾客的{info['topic']}。请自然地提问。\n"
            f"选项供参考: {', '.join(info['options'])}\n\n"
            "返回JSON: {\"question\": \"自然的问题文本\"}",
            ctx
        )
        question = result.get("question", f"想了解一下，{info['topic']}方面你感觉怎么样？")

        message = f"{prefix}\n\n{question}" if prefix else question

        return {
            "message": message,
            "stage": Stage.CONSTITUTION,
            "constitution_raw": json.dumps(raw, ensure_ascii=False),
            "constitution_extract_done": True,
            "constitution_questions_asked": questions_asked,
            "quick_replies": info["options"] + ["跳过"],
        }

    def _transition_to_scene_from_extract(self, state: dict, response: dict, ctx: str) -> dict:
        """Transition to SCENE stage, merging extraction results."""
        msg = self._chat(
            "体质了解结束。用一两句话总结了解到的体质信息，自然过渡到询问最近生活困扰。不要用括号或模板语言。",
            ctx
        )
        response["message"] = msg
        response["stage"] = Stage.SCENE
        response["quick_replies"] = ["睡眠不好", "消化不好", "容易疲劳", "皮肤问题", "想调理身体"]
        return response

    # ------------------------------------------------------------------
    # Stage: Scene
    # ------------------------------------------------------------------

    def _scene_ask(self, state: dict) -> dict:
        ctx = self._state_context(state)
        msg = self._chat(
            "询问顾客最近有什么困扰：睡眠、消化、疲劳、皮肤、调理身体等。",
            ctx
        )
        return {
            "message": msg, "stage": Stage.SCENE,
            "quick_replies": ["睡眠不好", "消化不好", "容易疲劳", "皮肤问题", "想调理身体"]
        }

    def _handle_scene(self, state: dict, user_input: str) -> dict:
        # Product intent pre-check — allow escape from scene
        keywords = ["有没有", "多少钱", "给我", "推给", "推荐", "我要",
                     "买", "不用", "算了", "直接", "就要", "只要", "来个", "还是"]
        if any(kw in user_input for kw in keywords):
            intent = self._detect_product_intent(state, user_input)
            if intent == "search_product" or intent == "show_catalog":
                return {"message": "", "stage": Stage.SCENE, "intent": intent}

        scene_raw = state.get("scene_raw", "")
        followup_done = state.get("scene_followup_done", False)
        ctx = self._state_context(state)

        if not scene_raw:
            result = self._chat_json(
                f"顾客描述困扰：「{user_input}」\n"
                "具体困扰→共情并追问细节；没有困扰→进入推荐；跳过→进入推荐\n"
                "意图：search_product/show_catalog/continue_flow\n"
                "JSON: {\"message\":\"...\",\"stage\":\"scene|recommend\",\"intent\":\"...\"}",
                ctx
            )
            next_stage = result.get("stage", Stage.SCENE)
            response = {"message": result.get("message", ""), "scene_raw": user_input,
                        "intent": result.get("intent", "continue_flow")}
            if next_stage == Stage.RECOMMEND:
                response["stage"] = Stage.RECOMMEND
                response["scene_followup_done"] = True
            else:
                response["stage"] = Stage.SCENE
            return response

        elif not followup_done:
            combined_scene = f"{scene_raw}；{user_input}"
            result = self._chat_json(
                f"顾客补充：「{user_input}」（之前：「{scene_raw}」）\n"
                "简短共情后告诉顾客马上分析推荐。不要问新问题。意图同上。\n"
                "JSON: {\"message\":\"...\",\"intent\":\"...\"}",
                ctx
            )
            result["stage"] = Stage.RECOMMEND
            result["scene_raw"] = combined_scene
            result["scene_followup_done"] = True
            return result

        else:
            result = self._chat_json(
                "告诉顾客马上分析推荐，不超过两句话。JSON: {\"message\":\"...\"}",
                ctx
            )
            result["stage"] = Stage.RECOMMEND
            return result

    def _handle_recommend(self, state: dict, user_input: str) -> dict:
        ctx = self._state_context(state)
        result = self._chat_json(
            f"推荐后顾客说：「{user_input}」\n"
            "想看更多→recommend；重测体质→constitution；改困扰→scene；道别→done；其他→recommend\n"
            "意图: search_product/show_catalog/continue_flow\n"
            "JSON: {\"message\":\"...\",\"stage\":\"recommend|scene|constitution|done\",\"intent\":\"...\"}",
            ctx
        )
        response = {"message": result.get("message", "好的，还有什么可以帮你的？")}
        next_stage = result.get("stage", Stage.RECOMMEND)
        response["stage"] = next_stage
        if next_stage == Stage.CONSTITUTION:
            response["constitution_extract_done"] = False
            response["constitution_questions_asked"] = 0
            response["constitution_raw"] = "{}"
            response["quick_replies"] = CONSTITUTION_ENTRY_REPLIES
        elif next_stage == Stage.RECOMMEND:
            response["quick_replies"] = ["推荐更多产品", "重新了解体质", "看看产品目录"]
        return response

    # ------------------------------------------------------------------
    # Stage: Catalog
    # ------------------------------------------------------------------

    def _handle_catalog(self, state: dict, user_input: str) -> dict:
        ctx = self._state_context(state)
        result = self._chat_json(
            f"看目录时顾客说：「{user_input}」\n"
            "看品类→介绍产品(stage:catalog)；想了解体质→constitution；想测体质→screening；道别→done\n"
            "意图：search_product/show_catalog/continue_flow\n"
            "JSON: {\"message\":\"...\",\"stage\":\"catalog|constitution|screening|done\",\"intent\":\"...\"}",
            ctx
        )
        response = {"message": result.get("message", "好的，还有什么可以帮你的？"),
                    "intent": result.get("intent", "continue_flow")}
        next_stage = result.get("stage", Stage.CATALOG)
        response["stage"] = next_stage
        if next_stage == Stage.CONSTITUTION:
            response["constitution_extract_done"] = False
            response["constitution_questions_asked"] = 0
            response["constitution_raw"] = "{}"
            response["quick_replies"] = CONSTITUTION_ENTRY_REPLIES
        elif next_stage == Stage.SCREENING:
            response["quick_replies"] = ["都没有", "在备孕或怀孕", "在哺乳期", "在吃处方药"]
        return response

    # ------------------------------------------------------------------
    # Stage: Done
    # ------------------------------------------------------------------

    def _handle_done(self, state: dict, user_input: str) -> dict:
        ctx = self._state_context(state)
        is_blocked = state.get("screening_result") == "blocked"
        result = self._chat_json(
            f"对话已经{'结束' if is_blocked else '告一段落'}。现在顾客说：「{user_input}」\n\n"
            "请灵活回应：\n"
            "- 顾客还想继续聊 → 根据上下文自然回应，可以返回 stage: catalog 让他看产品\n"
            "- 顾客说谢谢拜拜 → 温暖道别，返回 stage: done\n"
            "- 顾客问产品 → 介绍品类，返回 stage: catalog\n"
            "判断顾客意图：search_product / show_catalog / continue_flow\n\n"
            "返回JSON: {\"message\": \"...\", \"stage\": \"done|catalog\", \"intent\": \"search_product|show_catalog|continue_flow\"}",
            ctx
        )
        next_stage = result.get("stage", Stage.DONE)
        return {"message": result.get("message", "好的，随时欢迎回来。"), "stage": next_stage}
