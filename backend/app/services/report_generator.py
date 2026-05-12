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
        "scene_concern": scene_input,
        "bundle": [
            {
                "name": p.name,
                "ingredients": p.ingredients,
                "reason": f"此产品含有{p.ingredients}，适合偏{ctype}且关注{scene_input}的你。",
                "price": p.price or 0,
            }
            for p in recommendation.get("bundle", [])
        ],
        "disclaimer": "本报告基于传统食养理念，仅为调理建议参考，不构成医疗诊断。如有健康问题请咨询执业医师。",
    }