"""模拟 50 位顾客完整对话 + 下单流程"""
import requests
import json
import time
import random

BASE = "http://localhost:8002"
RNG = random.Random(42)

# 10体质 × 5人 = 50人
CUSTOMERS = []

names_pool = ["王丽", "李梅", "张兰", "刘芳", "陈秀", "杨英", "赵华", "黄红", "周娟", "吴波",
              "徐辉", "孙静", "胡杰", "朱涛", "高明", "林枫", "何雷", "郭鹏", "马燕", "罗琳",
              "郑强", "梁雪", "谢冰", "宋峰", "韩洁", "唐龙", "冯雨", "董云", "程磊", "曹阳",
              "袁鑫", "邓浩", "许颖", "傅海", "沈刚", "曾敏", "彭亮", "吕萍", "苏勇", "蒋玲",
              "蔡斌", "贾佳", "丁洋", "魏宁", "薛文", "叶超", "阎菲", "余峰", "潘岳", "杜辉"]

# Each constitution × 5 customers
CONSTITUTIONS = ["气虚质", "阳虚质", "阴虚质", "痰湿质", "湿热质",
                 "气郁质", "血瘀质", "血虚质", "特禀质", "平和质"]

DESCRIPTIONS = {
    "气虚质": ["最近总觉得累，没什么力气，稍微动一下就出汗",
               "特别容易疲劳，不想说话，总觉得气不够用",
               "一到下午就没精神，回家就想躺着",
               "走几步路就喘，比别人容易累很多",
               "总觉得身体被掏空了，特别容易感冒"],
    "阳虚质": ["手脚冰凉，冬天穿很多还是冷，不敢吃凉的",
               "特别怕冷，夏天也要穿长袖，肚子凉",
               "手脚一年四季都是凉的，腰膝酸冷",
               "比别人穿得多多了，还是觉得冷风往骨头里钻",
               "一到冬天就不想出门，手脚冻得跟冰块一样"],
    "阴虚质": ["口干想喝水，手心热，晚上出汗",
               "睡觉盗汗，经常口干咽燥，大便也干",
               "手心脚心发热，晚上睡不好，总想喝水",
               "皮肤干，嘴唇干，眼睛也干涩",
               "一到下午就手心发热，晚上翻来覆去睡不着"],
    "痰湿质": ["消化不好，肚子总是胀，大便不成形",
               "身体沉，觉得浑身黏糊糊的，大便黏马桶",
               "容易胖，吃一点就胀，口里黏黏的",
               "总感觉身体里全是水，浮肿，头也昏沉",
               "肚子大，吃什么都胀，大便稀软不成形"],
    "湿热质": ["脸上长痘，口苦口干，小便黄",
               "脸上油光光的，口臭，舌苔又黄又厚",
               "容易长湿疹，皮肤痒，大便黏臭",
               "一吃辣椒就长痘，脸上背上都是",
               "口苦得要命，早上起来舌苔黄黄的"],
    "气郁质": ["心情不好容易生气，胸闷总叹气",
               "总是闷闷不乐，胸口堵得慌，老想叹气",
               "容易焦虑烦躁，一生气就胁痛",
               "情绪波动大，一点小事就炸毛，胸闷",
               "总觉得心里堵着，不痛快，晚上想事情睡不着"],
    "血瘀质": ["肤色暗沉，容易瘀青，痛经有血块",
               "脸色暗暗的，嘴唇有点紫，舌下有青筋",
               "一碰就瘀青，好久才消，月经有血块",
               "皮肤色斑多，脸色不好看，经期肚子疼",
               "脸上的斑越来越多，身上也容易青一块紫一块"],
    "血虚质": ["面色苍白，头晕眼花，蹲下起来眼前发黑",
               "脸色白白的，嘴唇也白，经常头晕",
               "心慌心悸，睡眠浅多梦，记性也差",
               "站起来就眼前发黑，指甲也是白的",
               "月经量少，脸色萎黄，头发也掉得多"],
    "特禀质": ["皮肤容易过敏，一换季就打喷嚏",
               "一到春天就打喷嚏流鼻涕，皮肤起疹子",
               "过敏性鼻炎好多年了，闻到花粉就犯",
               "荨麻疹动不动就起，不知道对什么过敏",
               "一刮风就打喷嚏，身上痒，眼睛也痒"],
    "平和质": ["没什么特别的感觉，就是想日常调理一下",
               "身体还行，就是想了解下体质，日常保养",
               "最近感觉还行，就想看看适合吃什么",
               "朋友介绍来的，想了解下自己的身体",
               "没什么不舒服，就是想平时注意一下饮食"],
}

SCENES = {
    "气虚质": ["睡眠不好，睡得浅容易醒", "消化也不太好", "抵抗力差老感冒"],
    "阳虚质": ["消化不好，一吃凉的就不舒服", "关节有时候疼", "夜尿多"],
    "阴虚质": ["皮肤干痒", "失眠多梦", "便秘"],
    "痰湿质": ["大便黏马桶", "总觉得困想睡觉", "头昏沉沉的"],
    "湿热质": ["长痘痘", "湿疹痒得难受", "小便黄"],
    "气郁质": ["睡眠差，翻来覆去想事情", "胃口不好", "肩膀脖子僵硬"],
    "血瘀质": ["月经不调，有时候疼得厉害", "脸上色斑越来越多", "容易瘀青"],
    "血虚质": ["头晕得厉害", "睡眠很浅多梦", "容易心慌"],
    "特禀质": ["鼻炎老犯", "身上容易起疹子", "眼睛痒打喷嚏"],
    "平和质": ["想日常保健", "睡眠偶尔不好", "想了解一下体质"],
}

CHANNELS = ["wechat-dongmen", "wechat-ximen", "wechat-nanmen", "wechat-beimen", "wechat-zhongmen",
            "wechat-dongmen", "wechat-ximen", "wechat-nanmen", "wechat-beimen", "wechat-zhongmen"]


def simulate_customer(name, ctype, desc, scene, channel, idx):
    sid = f"sim-{idx:03d}"
    print(f"[{idx:02d}/50] {name} ({ctype}) ch={channel}")

    steps = [
        ("", None),
        ("都没有", None),
        (desc, None),
    ]

    result = None
    for i, (msg, _) in enumerate(steps):
        r = requests.post(f"{BASE}/api/chat/send",
                         json={"session_id": sid, "message": msg, "channel": channel},
                         timeout=60)
        result = r.json()
        time.sleep(0.3)

        # If differential needed
        if result.get("constitution_phase") == "differential":
            r = requests.post(f"{BASE}/api/chat/send",
                            json={"session_id": sid, "message": "第一个更多一些"},
                            timeout=60)
            result = r.json()
            time.sleep(0.3)

    # If still in differential (round 2)
    if result.get("constitution_phase") == "differential":
        r = requests.post(f"{BASE}/api/chat/send",
                        json={"session_id": sid, "message": "第一个"},
                        timeout=60)
        result = r.json()
        time.sleep(0.3)

    # Scene step
    r = requests.post(f"{BASE}/api/chat/send",
                     json={"session_id": sid, "message": RNG.choice(scene)},
                     timeout=60)
    result = r.json()
    time.sleep(0.3)

    # Get conversation from DB
    r_conv = requests.get(f"{BASE}/api/staff/conversations?page=1&page_size=1")
    convs = r_conv.json().get("conversations", [])
    conv = convs[0] if convs else None

    if not conv:
        print(f"  WARN: no conversation found")
        return None

    # Get recommendation products from the constitution bundle
    ctype_key = conv.get("constitution_type") or ctype
    r_bundle = requests.get(f"{BASE}/api/staff/constitution-bundles")
    bundles = r_bundle.json()
    bundle_products = bundles.get(ctype_key, [])[:3]  # take top 3

    # Build order items
    items = []
    total = 0.0
    for bp in bundle_products:
        price = float(bp.get("price", 0) or RNG.uniform(25, 68))
        qty = RNG.randint(1, 2)
        items.append({
            "sku_id": bp.get("sku_id", ""),
            "name": bp.get("name", "产品"),
            "category": bp.get("category", ""),
            "price": round(price, 2),
            "quantity": qty,
        })
        total += price * qty

    if not items:
        # Fallback: pick random products
        r_prods = requests.get(f"{BASE}/api/staff/products?page=1&page_size=10")
        prods = r_prods.json().get("products", [])
        for p in prods[:3]:
            price = float(p.get("price", 0) or RNG.uniform(25, 68))
            items.append({
                "sku_id": p["sku_id"],
                "name": p.get("name", "产品"),
                "category": p.get("category", ""),
                "price": round(price, 2),
                "quantity": 1,
            })
            total += price

    # Get full conversation snapshots
    r_detail = requests.get(f"{BASE}/api/staff/conversations/{conv['id']}")
    conv_detail = r_detail.json() if r_detail.status_code == 200 else conv

    # Create order
    order_no = f"SIM{idx:04d}{int(time.time())}"
    order_payload = {
        "order_no": order_no,
        "customer_nickname": name,
        "customer_phone": f"138{idx:08d}"[:11],
        "total_amount": round(total, 2),
        "items": items,
        "conversation_snapshot": {
            "id": conv["id"],
            "stage": conv.get("stage", ""),
            "stage_history": conv.get("stage_history", []),
            "messages_history": conv_detail.get("messages_history", [])[-6:],  # last 6
        },
        "recommendation_snapshot": {
            "constitution_type": ctype_key,
            "products": items,
            "total": round(total, 2),
        },
        "constitution_snapshot": {
            "type": ctype_key,
            "confidence": conv.get("constitution_confidence", 0),
            "description": DESCRIPTIONS.get(ctype, [""])[0],
        },
    }

    r_order = requests.post(f"{BASE}/api/staff/orders", json=order_payload, timeout=30)
    if r_order.status_code == 200:
        order = r_order.json()
        print(f"  => Order #{order['id']}: {len(items)} items, {total:.2f}")
        return order
    elif r_order.status_code == 409:
        print(f"  => Duplicate, retrying...")
        order_payload["order_no"] = f"SIM{idx:04d}{int(time.time())}R"
        r_order = requests.post(f"{BASE}/api/staff/orders", json=order_payload, timeout=30)
        if r_order.status_code == 200:
            order = r_order.json()
            print(f"  => Order #{order['id']}: {len(items)} items, {total:.2f}")
            return order
    print(f"  => FAIL: {r_order.status_code} {r_order.text[:80]}")
    return None


# ── Main ──
print("=" * 60)
print("  50 Customer Simulation")
print("=" * 60)

results = []
idx = 0
for ctype in CONSTITUTIONS:
    for i in range(5):
        name = names_pool[idx]
        desc = DESCRIPTIONS[ctype][i]
        channel = CHANNELS[idx % len(CHANNELS)]
        order = simulate_customer(name, ctype, desc, SCENES[ctype], channel, idx + 1)
        if order:
            results.append(order)
        else:
            print(f"  SKIP: failed to complete")
        idx += 1
        time.sleep(0.5)  # rate limit

print()
print("=" * 60)
print(f"  COMPLETE: {len(results)}/50 orders created")
print("=" * 60)

# ── Verify ──
print()
print("=== Verification ===")
r = requests.get(f"{BASE}/api/staff/orders?page=1&page_size=1")
total_orders = r.json()["total"]
print(f"Total orders: {total_orders}")

r = requests.get(f"{BASE}/api/staff/conversations?page=1&page_size=1")
total_convs = r.json()["total"]
print(f"Total conversations: {total_convs}")

# Check snapshots
r = requests.get(f"{BASE}/api/staff/orders?page=1&page_size=50")
orders = r.json().get("orders", [])
with_conv = sum(1 for o in orders if o.get("conversation_snapshot"))
with_rec = sum(1 for o in orders if o.get("recommendation_snapshot"))
with_const = sum(1 for o in orders if o.get("constitution_snapshot"))
with_items = sum(1 for o in orders if o.get("items"))
print(f"Orders with conversation_snapshot: {with_conv}/{len(orders)}")
print(f"Orders with recommendation_snapshot: {with_rec}/{len(orders)}")
print(f"Orders with constitution_snapshot: {with_const}/{len(orders)}")
print(f"Orders with items: {with_items}/{len(orders)}")
