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
    "痰湿质": {
        "exercise": "适合中等强度有氧运动如慢跑、快走、骑行、游泳，每周至少4次，每次40分钟以上，出汗排湿效果最佳。",
        "rest": "避免熬夜和久坐，居住环境保持通风干燥。衣物被褥勤晾晒，避免潮湿环境。",
        "emotion": "痰湿体质易困重懒动。多参加户外活动，听节奏明快的音乐提振精神。设定小目标，逐步培养运动习惯。",
        "daily": "晨起喝一杯温开水清肠。少食甜腻、油腻食物，控制食量七八分饱。常饮薏米茶、陈皮茶祛湿。"
    },
    "血瘀质": {
        "exercise": "适合促进血液循环的运动如快走、慢跑、舞蹈、游泳，每周3-5次，每次30分钟以上。避免久坐久站。",
        "rest": "保证充足睡眠，避免熬夜伤肝血。睡前可温水泡脚15分钟促进循环。",
        "emotion": "血瘀易致情绪低落压抑。多与人交流倾诉，培养兴趣爱好转移注意力。听轻松愉悦的音乐放松心情。",
        "daily": "晨起一杯温水加几片山楂活血。注意保暖，尤其腰腹部。少食寒凉，可常饮玫瑰花茶或山楂茶。"
    },
    "气郁质": {
        "exercise": "适合舒展性运动如瑜伽、太极、舞蹈、散步。户外运动尤其有益，接触自然环境有助于心情舒畅。",
        "rest": "规律作息，避免熬夜。睡前可泡澡或听轻音乐放松。卧室保持安静、温暖。",
        "emotion": "气郁质核心在情绪调节。多参加社交活动，与人倾诉。练习冥想、深呼吸。培养能让自己开心的爱好。",
        "daily": "晨起喝一杯玫瑰花茶疏肝解郁。少吃辛辣刺激食物。多食柑橘、香蕉等令人愉悦的食物。保持居室明亮通风。"
    },
    "血虚质": {
        "exercise": "适合温和运动如散步、瑜伽、太极，避免剧烈运动和大量出汗。运动时间不宜过长，以不感到疲劳为度。",
        "rest": "保证充足睡眠，早睡早起，午休20-30分钟。避免熬夜和用眼过度。睡眠环境宜安静、温暖。",
        "emotion": "血虚易心悸不安。练习静坐冥想，听舒缓音乐。避免过度思虑和紧张。",
        "daily": "晨起一杯红枣枸杞水补血。多吃红色和黑色食物如红枣、桂圆、黑芝麻。避免长时间看手机电脑。"
    },
    "特禀质": {
        "exercise": "选择室内运动为主如瑜伽、太极、游泳（室内），避免在花粉季节户外运动。运动前充分热身。",
        "rest": "保持规律作息增强免疫力。卧室勤打扫除螨，使用防过敏寝具。空气净化器有帮助。",
        "emotion": "过敏症状易导致焦虑。学会接受自身体质特点，保持平和心态。与同样情况的人交流经验。",
        "daily": "注意避开已知过敏原，换季时戴口罩防护。饮食清淡，少吃海鲜、芒果等易致敏食物。增强免疫力的黄芪水可常饮。"
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
    "痰湿质": {
        "recommend": "薏米、赤小豆、茯苓、山药、冬瓜、白萝卜、海带、鲫鱼、陈皮、荷叶",
        "avoid": "甜腻糕点、肥肉、油炸食品、奶油、冰淇淋、过量米面主食",
        "cooking": "以清蒸、煮、凉拌为主。少油少盐，多用醋、姜、陈皮调味。",
        "tea": "薏米茯苓茶、陈皮普洱茶、冬瓜荷叶茶、山楂决明子茶"
    },
    "血瘀质": {
        "recommend": "山楂、黑豆、茄子、洋葱、大蒜、醋、桃仁、红花（少量）、玫瑰花、月季花",
        "avoid": "寒凉食物如冰镇饮料、苦瓜、西瓜（冬季），肥甘厚腻阻碍气血运行",
        "cooking": "可多用醋、酒酿、姜葱蒜等活血调料。少食寒凉烹调的冷盘。",
        "tea": "山楂红糖水、玫瑰花茶、桃仁茶（少量）、丹参茶"
    },
    "气郁质": {
        "recommend": "柑橘、佛手、玫瑰花、茉莉花、薄荷、小麦、大麦、黄花菜、香蕉、金橘",
        "avoid": "过量咖啡、浓茶、高度白酒等刺激性饮品，辛辣燥热食物加重烦躁",
        "cooking": "清淡为主，多食疏肝理气食材。色彩搭配鲜艳有助提升食欲和心情。",
        "tea": "玫瑰花茶、佛手柑茶、茉莉花茶、薄荷柠檬茶"
    },
    "血虚质": {
        "recommend": "红枣、桂圆、当归、枸杞、黑芝麻、猪肝、瘦肉、菠菜、黑木耳、红豆",
        "avoid": "生冷食物耗伤脾胃影响气血生化，浓茶、咖啡影响铁吸收",
        "cooking": "以炖、蒸、煮为主，善用当归、黄芪煲汤。食物质地宜软烂易消化。",
        "tea": "红枣桂圆茶、当归枸杞茶、黑芝麻糊、五红汤（红豆红枣红糖红皮花生枸杞）"
    },
    "特禀质": {
        "recommend": "黄芪、白术、防风、灵芝、山药、红枣、蜂蜜、百合、银耳",
        "avoid": "个人已知过敏食物严格避开。海鲜、芒果、菠萝、蚕豆等常见致敏食物需留意",
        "cooking": "食材新鲜为主，避免过多添加剂和防腐剂。充分加热熟透后食用。",
        "tea": "黄芪红枣茶、防风白术茶（少量）、灵芝水、蜂蜜柠檬水（非过敏者）"
    },
}

SEASONAL_TIPS = {
    "气虚质": "春捂秋冻，春季注意防风避寒，可食韭菜、春笋助阳气生发。夏季避免过度贪凉，空调温度不宜过低。秋季适当进补，山药、红枣当季最宜。冬季早卧晚起，食羊肉、牛肉温补。",
    "阳虚质": "春夏是养阳黄金期，多晒太阳、多户外活动，可食韭菜、生姜助阳。秋季开始注意保暖，尤其腰膝。冬季是进补最佳时节，当归生姜羊肉汤、桂圆红枣茶正当其时。",
    "阴虚质": "春季多风干燥，注意润肺，可食梨、百合。夏季避免暴晒和大汗，及时补水。秋季是养阴关键期，银耳、百合、梨正当季。冬季室内暖气干燥，注意加湿，多饮温水。",
    "湿热质": "春季湿气重，可食薏米、赤小豆祛湿。夏季是清热利湿最佳时节，冬瓜、绿豆、苦瓜正当季。秋季减少油腻，清淡饮食。冬季进补注意不宜滋腻，清补为主。",
    "平和质": "春生夏长，顺应阳气生发，多户外活动。秋收冬藏，适当进补，早睡晚起。四季饮食应季而食，保持平衡。",
    "痰湿质": "春季湿气重，重点祛湿，多食薏米、赤小豆、茯苓。夏季是排湿黄金期，运动出汗最宜，冬瓜、荷叶正当季。秋季减少甜腻，以清淡为主。冬季不宜滋腻进补，清补为宜。",
    "血瘀质": "春季万物生发，是活血最佳季节，多户外运动，食山楂、玫瑰花。夏季避免贪凉，适当出汗促进循环。秋季干燥，注意润燥活血，食黑木耳、山楂。冬季注意保暖，适量饮酒酿暖身活血。",
    "气郁质": "春季养肝正当时，多踏青赏花，食玫瑰花、佛手、柑橘疏肝理气。夏季避免烦躁，适当午休，饮食清爽。秋季易悲秋伤怀，多与人交流，赏菊登高。冬季多晒太阳，保持室内明亮温暖。",
    "血虚质": "春季宜养血柔肝，食红枣、枸杞、菠菜。夏季避免过度出汗耗血，午休养心。秋季是补血最佳季节，当归、桂圆、红枣正当季。冬季早睡晚起养阴血，适当进补羊肉、当归汤。",
    "特禀质": "春季花粉季注意防护，外出戴口罩，减少户外活动。夏季空调房注意保暖，避免冷热交替刺激。秋季换季早晚温差大，及时增减衣物，预防感冒。冬季增强免疫力，适当进补黄芪、灵芝。",
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
                    customer_name: str = "", constitution_type: str = None) -> dict:
    if constitution_type:
        ctype = constitution_type
        const = {"constitution_type": ctype, "description": "", "all_scores": {}}
    else:
        const = analyze(constitution_raw)
        ctype = const["constitution_type"]
    food = FOOD_TIPS.get(ctype, FOOD_TIPS["平和质"])
    life = LIFESTYLE_TIPS.get(ctype, LIFESTYLE_TIPS["平和质"])
    seasonal = SEASONAL_TIPS.get(ctype, SEASONAL_TIPS["平和质"])

    # Merge fixed_bundle + llm_recommendations into a single bundle
    bundle = list(recommendation.get("bundle", []))
    if not bundle:
        bundle = list(recommendation.get("fixed_bundle", [])) + list(recommendation.get("llm_recommendations", []))

    # Build conversation summary
    summary_parts = []
    if ctype and ctype != "平和质":
        summary_parts.append(f"经AI体质辨识，你属于{ctype}，{'、'.join([k for k,v in const.get('all_scores',{}).items() if v > 0][:2]) if const.get('all_scores') else ''}")
    elif ctype == "平和质":
        summary_parts.append("经AI体质辨识，你的体质比较平和，阴阳调和，是理想的健康状态")
    if scene_input:
        summary_parts.append(f"你提到的主要困扰是「{scene_input[:30]}」")
    summary_parts.append(f"为你推荐了{len(bundle)}款药食同源产品")
    summary = "。".join(summary_parts) + "。"

    return {
        "customer_name": customer_name,
        "constitution_type": ctype,
        "constitution_desc": const.get("description", ""),
        "all_scores": const.get("all_scores", {}),
        "summary": summary,
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
            for p in bundle
        ],
        "disclaimer": "本报告基于传统食养理念，仅为调理建议参考，不构成医疗诊断。如有健康问题请咨询执业医师。",
    }