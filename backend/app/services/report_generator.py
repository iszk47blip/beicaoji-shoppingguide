# backend/app/services/report_generator.py
from app.services.constitution_analyzer import analyze

LIFESTYLE_TIPS = {
    "气虚质": "日常可适当快走、八段锦等温和运动，不宜大汗淋漓。作息规律，避免熬夜耗气。",
    "阳虚质": "适合晨练、太极拳，多晒太阳。饮食宜温热，少食生冷。",
    "阴虚质": "避免剧烈运动和高温环境，可练习瑜伽、冥想。少熬夜，多补充水分。",
    "湿热质": "适合中等强度运动如慢跑、游泳，出汗有助于排湿。少吃油腻甜腻食物。",
    "平和质": "保持现状即可。四季饮食顺应时节，劳逸结合。",
}

FOOD_TIPS = {
    "气虚质": "适合：山药、红枣、莲子、小米、牛肉、鸡肉等健脾益气的食材。",
    "阳虚质": "适合：羊肉、韭菜、核桃、桂圆、生姜等温补阳气的食材。",
    "阴虚质": "适合：银耳、百合、梨、鸭肉、枸杞等滋阴润燥的食材。",
    "湿热质": "适合：薏米、绿豆、冬瓜、苦瓜、赤小豆等清热利湿的食材。",
    "平和质": "均衡饮食，各种食材都可适量摄入。",
}

SEASONAL_TIPS = {
    "气虚质": "春季注意防风保暖，夏季不宜过度贪凉，秋冬进补以平补为主。",
    "阳虚质": "春夏养阳，多晒太阳。秋冬注意保暖，尤其腰腹部和双脚。",
    "阴虚质": "秋冬注意润燥，少吃辛辣。夏季避免暴晒和大量出汗。",
    "湿热质": "夏季重点清热利湿，少吃冷饮。秋冬进补不宜滋腻。",
    "平和质": "随季节变化适当调整，春夏养阳，秋冬养阴。",
}

INGREDIENT_BENEFITS = {
    "百合": "养心安神，清心除烦",
    "酸枣仁": "养心安神，助眠安睡",
    "茯苓": "健脾利湿，宁心安神",
    "山药": "健脾益气，养胃和中",
    "莲子": "补脾止泻，养心安神",
    "枸杞": "滋补肝肾，益精明目",
    "红枣": "补中益气，养血安神",
    "桂圆": "补益心脾，养血安神",
    "玫瑰花": "行气解郁，舒缓情绪",
    "薏仁": "健脾利湿，清热排浊",
    "赤小豆": "利水消肿，清热解毒",
    "陈皮": "理气健脾，燥湿化痰",
    "山楂": "消食健胃，行气散瘀",
    "麦冬": "养阴润肺，清心除烦",
    "桑葚": "滋阴补血，润肠通便",
    "核桃": "温补阳气，补肾健脑",
    "生姜": "温中散寒，暖身驱寒",
    "肉桂": "温补肾阳，散寒暖身",
    "黄芪": "补气固表，提升精力",
    "党参": "补中益气，健脾养胃",
    "银耳": "滋阴润肺，养胃生津",
    "绿豆": "清热解毒，消暑利水",
    "黑芝麻": "补肝肾，益精血",
    "芡实": "补脾止泻，益肾固精",
    "当归": "补血活血，调经暖身",
    "菊花": "清肝明目，疏风清热",
    "薄荷": "疏散风热，清利头目",
    "知母": "清热泻火，滋阴润燥",
    "雪梨": "清热润肺，生津止渴",
    "干姜": "温中散寒，回阳通脉",
    "花椒": "温中散寒，暖胃驱寒",
    "小茴香": "温中散寒，理气和胃",
    "玉竹": "养阴润燥，生津止渴",
    "生地": "清热凉血，养阴生津",
    "荷叶": "清热解暑，升发清阳",
}


def _ingredient_reason(name: str, ingredients: str, constitution_type: str, scene: str) -> str:
    """Generate a specific reason based on product ingredients."""
    parts = []
    for kw, benefit in INGREDIENT_BENEFITS.items():
        if ingredients and kw in ingredients:
            parts.append(f"「{kw}」{benefit}")
    if parts:
        detail = "；".join(parts[:3])
        return f"{name}含{detail}。对于偏{constitution_type}又关注{scene}的你来说，这些成分能起到很好的食养辅助作用。"
    return f"{name}的成分搭配适合偏{constitution_type}且关注{scene}的你，日常食用有助调理。"


def generate_report(constitution_raw: str, scene_input: str, recommendation: dict,
                    customer_name: str = "") -> dict:
    const = analyze(constitution_raw)
    ctype = const["constitution_type"]
    return {
        "customer_name": customer_name,
        "constitution_type": ctype,
        "constitution_desc": const["description"],
        "food_advice": FOOD_TIPS.get(ctype, FOOD_TIPS["平和质"]),
        "lifestyle_advice": LIFESTYLE_TIPS.get(ctype, LIFESTYLE_TIPS["平和质"]),
        "seasonal_advice": SEASONAL_TIPS.get(ctype, SEASONAL_TIPS["平和质"]),
        "scene_concern": scene_input,
        "bundle": [
            {
                "name": p if isinstance(p, str) else (p.get("name", "") if isinstance(p, dict) else getattr(p, "name", "")),
                "category": "" if isinstance(p, str) else (p.get("category", "") if isinstance(p, dict) else getattr(p, "category", "")),
                "ingredients": "" if isinstance(p, str) else (p.get("ingredients", "") if isinstance(p, dict) else getattr(p, "ingredients", "")),
                "reason": _ingredient_reason(
                    p if isinstance(p, str) else (p.get("name", "") if isinstance(p, dict) else getattr(p, "name", "")),
                    "" if isinstance(p, str) else (p.get("ingredients", "") if isinstance(p, dict) else getattr(p, "ingredients", "")),
                    ctype,
                    scene_input,
                ),
                "price": 0 if isinstance(p, str) else (p.get("price", 0) if isinstance(p, dict) else getattr(p, "price", 0) or 0),
            }
            for p in recommendation.get("bundle", [])
        ],
        "disclaimer": "本报告基于传统食养理念，仅为调理建议参考，不构成医疗诊断。如有健康问题请咨询执业医师。",
    }