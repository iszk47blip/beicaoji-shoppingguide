# backend/app/services/constitution_analyzer.py
import json
import re


def _fuzzy_match(user_answer: str, expected: str) -> bool:
    """Check if user_answer matches expected, with fuzzy fallback for LLM output variance."""
    if not user_answer or not expected:
        return False
    if expected in user_answer:
        return True
    # Remove punctuation and whitespace for comparison
    a = re.sub(r'[，。！？、\s]', '', user_answer)
    b = re.sub(r'[，。！？、\s]', '', expected)
    return a == b


CONSTITUTION_RULES = {
    "气虚质": {
        "signals": {"qi_deficiency": ["是，经常觉得累、不想说话"],
                     "temperature_tendency": ["偏凉，冬天容易手脚冰凉"]},
        "description": "偏气虚体质。这种体质的人通常容易疲劳、气短懒言、精神不振，容易出虚汗。日常适合多食用健脾益气的食物。",
        "avoid_tags": ["清热", "泻下", "寒凉"],
        "prefer_tags": ["补气", "健脾", "温补"],
    },
    "阳虚质": {
        "signals": {"temperature_tendency": ["偏凉，冬天容易手脚冰凉"],
                     "sweat_tendency": ["几乎不出汗，比别人汗少"]},
        "description": "偏阳虚体质。阳气不足，畏寒怕冷，手脚常年偏凉。适合温补阳气的食养方向。",
        "avoid_tags": ["清热", "寒凉", "泻下"],
        "prefer_tags": ["温补", "补阳", "补气"],
    },
    "阴虚质": {
        "signals": {"heat_signs": ["经常，动不动就上火"],
                     "sweat_tendency": ["稍微一动就容易出汗"]},
        "description": "偏阴虚体质。体内津液不足，容易口干、手心热、盗汗。适合滋阴润燥的食养方向。",
        "avoid_tags": ["温补", "补阳", "辛热"],
        "prefer_tags": ["滋阴", "润燥", "清热"],
    },
    "湿热质": {
        "signals": {"damp_heat": ["经常这样"],
                     "heat_signs": ["经常，动不动就上火"]},
        "description": "偏湿热体质。体内湿气和热邪并存，常见口苦、大便黏滞、皮肤易出油。适合清热利湿的食养方向。",
        "avoid_tags": ["温补", "滋腻", "补气"],
        "prefer_tags": ["清热", "利湿", "健脾"],
    },
    "痰湿质": {
        "signals": {"stool_digest": ["大便容易黏滞或不成形"],
                     "damp_heat": ["经常这样"]},
        "description": "偏痰湿体质。体内痰湿较重，容易腹胀、大便黏滞、身体沉重。适合健脾利湿、化痰的食养方向。",
        "avoid_tags": ["滋腻", "寒凉", "润下"],
        "prefer_tags": ["健脾", "利湿", "化痰"],
    },
    "血瘀质": {
        "signals": {"blood_combined": ["经常瘀青或眼前发黑（两项都有或一项经常）",
                                       "经常瘀青"]},
        "description": "偏血瘀体质。血液循环不畅，容易出现瘀斑、经期血块、疼痛固定等表现。适合活血化瘀的食养方向。",
        "avoid_tags": ["寒凉", "润下"],
        "prefer_tags": ["活血", "化瘀", "温通"],
    },
    "血虚质": {
        "signals": {"blood_combined": ["经常眼前发黑"]},
        "description": "偏血虚体质。血液不足，容易头晕眼花、面色苍白、记忆力减退。适合补血养血的食养方向。",
        "avoid_tags": ["清热", "泻下", "辛散"],
        "prefer_tags": ["补血", "养血", "健脾"],
    },
    "气郁质": {
        "signals": {"emotion": ["经常情绪波动大"]},
        "description": "偏气郁体质。气机郁滞，情绪容易波动、胁肋胀痛、多愁善感。适合疏肝解郁的食养方向。",
        "avoid_tags": ["辛热", "温补过度"],
        "prefer_tags": ["疏肝", "解郁", "理气"],
    },
    "特禀质": {
        "signals": {"allergy": ["经常过敏"]},
        "description": "偏特禀体质（过敏体质）。对外界刺激敏感，容易出现过敏反应。建议避开已知过敏原，产品选择前需仔细确认成分。",
        "avoid_tags": [],
        "prefer_tags": ["增强免疫"],
    },
    "平和质": {
        "signals": {},
        "description": "体质比较平和，阴阳气血协调。继续保持健康的生活方式即可，也可以根据季节适当调理。",
        "avoid_tags": [],
        "prefer_tags": [],
    },
}

def analyze(constitution_raw: str) -> dict:
    """分析体质原始回答，返回体质倾向结果"""
    answers = json.loads(constitution_raw) if isinstance(constitution_raw, str) else constitution_raw
    scores = {}
    for ctype, rules in CONSTITUTION_RULES.items():
        score = 0
        for field, expected_answers in rules["signals"].items():
            user_answer = answers.get(field, "")
            if any(_fuzzy_match(user_answer, ea) for ea in expected_answers):
                score += 1
        scores[ctype] = score
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        best = "平和质"
    result = CONSTITUTION_RULES[best]
    return {
        "constitution_type": best,
        "score": scores[best],
        "description": result["description"],
        "avoid_tags": result["avoid_tags"],
        "prefer_tags": result["prefer_tags"],
        "all_scores": scores,
    }