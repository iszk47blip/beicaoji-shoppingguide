# backend/app/services/constitution_analyzer.py
import json

CONSTITUTION_RULES = {
    "气虚质": {
        "signals": {"qi_deficiency": ["是，经常觉得累、不想说话"],
                     "cold_hot": ["偏凉，冬天容易手脚冰凉"]},
        "description": "偏气虚体质。这种体质的人通常容易疲劳、气短懒言、精神不振，容易出虚汗。日常适合多食用健脾益气的食物。",
        "avoid_tags": ["清热", "泻下", "寒凉"],
        "prefer_tags": ["补气", "健脾", "温补"],
    },
    "阳虚质": {
        "signals": {"temperature_tendency": ["偏凉，冬天容易手脚冰凉"],
                     "cold_hot_bias": ["明显怕冷，比别人穿得多"]},
        "description": "偏阳虚体质。阳气不足，畏寒怕冷，手脚常年偏凉。适合温补阳气的食养方向。",
        "avoid_tags": ["清热", "寒凉", "泻下"],
        "prefer_tags": ["温补", "补阳", "补气"],
    },
    "阴虚质": {
        "signals": {"heat_signs": ["经常，动不动就上火"],
                     "cold_hot_bias": ["明显怕热，容易出汗"]},
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
            if any(ea in user_answer for ea in expected_answers):
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