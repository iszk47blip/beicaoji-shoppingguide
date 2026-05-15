# backend/app/services/report_generator.py
from app.services.constitution_analyzer import analyze

LIFESTYLE_TIPS = {
    "气虚质": {
        "exercise": "适合快走、八段锦、太极拳等温和运动，每次20-30分钟，微微出汗即可。不宜剧烈运动和大汗淋漓，以免耗气。",
        "rest": "保证充足睡眠，建议晚上10点前入睡。中午可小憩15-30分钟养神。避免熬夜和过度劳累。",
        "emotion": "气虚之人易思虑过度。可练习深呼吸、冥想，遇事多与人交流，不要独自烦恼。",
        "daily": "晨起喝一杯温蜂蜜水补气暖胃。注意保暖，尤其背部和小腹。减少长时间说话和用脑过度。"
    },
    "阳虚质": {
        "exercise": "适合晨练，太阳出来后运动最佳。推荐太极拳、散步、八段锦。运动前充分热身，以身体发热为度。",
        "rest": "晚上11点前入睡，早晨可适当晚起以养阳气。避免在阴冷潮湿的环境中久待。",
        "emotion": "多与人交往，参与集体活动。听温暖欢快的音乐，避免独处时情绪低落。阳光充足时多出门走走。",
        "daily": "晨起喝一杯姜枣茶暖身。坚持用温水泡脚15-20分钟。穿衣注意腰腹和双脚保暖，不贪凉。"
    },
    "阴虚质": {
        "exercise": "适合瑜伽、太极、游泳等柔缓运动，避免高温瑜伽和大强度训练。运动后及时补充水分。",
        "rest": "保证充足睡眠，午休20-30分钟。避免熬夜，晚上11点前入睡。睡眠环境宜安静、温度稍低。",
        "emotion": "阴虚易烦躁焦虑。可通过书法、茶道、听轻音乐等方式静心。遇事深呼吸，不急不躁。",
        "daily": "晨起一杯温蜂蜜水或梨水润燥。少食辛辣烧烤油炸食物。保持室内适宜湿度，可用加湿器。"
    },
    "湿热质": {
        "exercise": "适合中等强度有氧运动如慢跑、游泳、骑行，出汗有助排湿。每周3-4次，每次30分钟以上。",
        "rest": "保持规律作息，避免熬夜。居住环境保持通风干燥，避免潮湿。衣物被褥勤晾晒。",
        "emotion": "湿热易致烦躁易怒。可通过运动释放情绪，也可与朋友聊天排解。避免压抑情绪。",
        "daily": "晨起一杯温开水清肠。少吃油腻、甜腻、辛辣食物。可常饮薏米茶或绿茶清热利湿。"
    },
    "平和质": {
        "exercise": "保持每周3-4次适度运动，快走、游泳、球类均可。注意循序渐进，不过度。",
        "rest": "保持规律作息，早睡早起。睡眠7-8小时为宜。劳逸结合，不过劳。",
        "emotion": "保持乐观平和的心态，培养兴趣爱好。与家人朋友保持良好沟通。",
        "daily": "饮食均衡，荤素搭配。顺应四时变化调整作息和饮食。定期体检，防患未然。"
    },
}

FOOD_TIPS = {
    "气虚质": {
        "recommend": "山药、红枣、莲子、小米、粳米、牛肉、鸡肉、鸡蛋、蜂蜜、香菇",
        "avoid": "生冷食物、冰镇饮料、过量苦寒之物如苦瓜、绿豆（少量可）",
        "cooking": "以蒸、炖、煮为主，少油炸。食材宜细碎易消化，粥品尤其适合。",
        "tea": "黄芪红枣茶、山药莲子羹、红枣枸杞茶"
    },
    "阳虚质": {
        "recommend": "羊肉、牛肉、韭菜、核桃、桂圆、生姜、肉桂、小茴香、花椒、板栗",
        "avoid": "生冷瓜果、冰镇食物、螃蟹等寒凉海鲜、绿茶（少喝）",
        "cooking": "可适当多用炖、焖、红烧。善用姜、葱、蒜、肉桂等温热调料。",
        "tea": "姜枣红糖茶、桂圆枸杞茶、肉桂蜂蜜水"
    },
    "阴虚质": {
        "recommend": "银耳、百合、梨、鸭肉、猪肉、枸杞、桑葚、黑芝麻、蜂蜜、牛奶",
        "avoid": "辛辣燥热之物如辣椒、花椒、羊肉串、烧烤、高度白酒",
        "cooking": "以蒸、煮、炖为主，少煎炒。汤羹类尤其养阴。",
        "tea": "银耳百合羹、雪梨蜂蜜水、桑葚枸杞茶、麦冬茶"
    },
    "湿热质": {
        "recommend": "薏米、赤小豆、绿豆、冬瓜、苦瓜、莲藕、芹菜、黄瓜、鲫鱼、鸭肉",
        "avoid": "油腻肥甘、甜腻糕点、烧烤煎炸、过量饮酒、辛辣火锅",
        "cooking": "以清蒸、凉拌、快炒为主。少油少盐，保持食材本味。",
        "tea": "薏米赤小豆茶、冬瓜荷叶茶、菊花绿茶、陈皮普洱茶"
    },
    "平和质": {
        "recommend": "各类食材均衡摄入，五谷杂粮、蔬菜水果、鱼肉蛋奶搭配合理",
        "avoid": "无明显禁忌，但应避免长期偏食某类食物",
        "cooking": "蒸煮炒炖皆可，保持食材多样性。",
        "tea": "根据季节选择：春饮花茶、夏饮绿茶、秋饮乌龙、冬饮红茶"
    },
}

SEASONAL_TIPS = {
    "气虚质": "春捂秋冻，春季注意防风避寒，可食韭菜、春笋助阳气生发。夏季避免过度贪凉，空调温度不宜过低。秋季适当进补，山药、红枣当季最宜。冬季早卧晚起，食羊肉、牛肉温补。",
    "阳虚质": "春夏是养阳黄金期，多晒太阳、多户外活动，可食韭菜、生姜助阳。秋季开始注意保暖，尤其腰膝。冬季是进补最佳时节，当归生姜羊肉汤、桂圆红枣茶正当其时。",
    "阴虚质": "春季多风干燥，注意润肺，可食梨、百合。夏季避免暴晒和大汗，及时补水。秋季是养阴关键期，银耳、百合、梨正当季。冬季室内暖气干燥，注意加湿，多饮温水。",
    "湿热质": "春季湿气重，可食薏米、赤小豆祛湿。夏季是清热利湿最佳时节，冬瓜、绿豆、苦瓜正当季。秋季减少油腻，清淡饮食。冬季进补注意不宜滋腻，清补为主。",
    "平和质": "春生夏长，顺应阳气生发，多户外活动。秋收冬藏，适当进补，早睡晚起。四季饮食应季而食，保持平衡。",
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
    food = FOOD_TIPS.get(ctype, FOOD_TIPS["平和质"])
    life = LIFESTYLE_TIPS.get(ctype, LIFESTYLE_TIPS["平和质"])
    seasonal = SEASONAL_TIPS.get(ctype, SEASONAL_TIPS["平和质"])
    return {
        "customer_name": customer_name,
        "constitution_type": ctype,
        "constitution_desc": const["description"],
        "all_scores": const.get("all_scores", {}),
        "food_advice": food,
        "lifestyle_advice": life,
        "seasonal_advice": seasonal,
        "scene_concern": scene_input,
        "bundle": [
            {
                "name": p if isinstance(p, str) else (p.get("name", "") if isinstance(p, dict) else getattr(p, "name", "")),
                "sku_id": "" if isinstance(p, str) else (p.get("sku_id", "") if isinstance(p, dict) else getattr(p, "sku_id", "")),
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