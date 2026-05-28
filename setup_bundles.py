"""配置 10 体质套餐 — 每个体质 6-8 件产品（核心+搭配+锦上添花）"""
import requests, json, time

BASE = "http://localhost:8002"

# Load all products
all_products = {}
cats_r = requests.get(f"{BASE}/api/staff/categories")
for cat in cats_r.json()['categories']:
    r = requests.get(f"{BASE}/api/staff/products?category={cat['name']}&page_size=200")
    for p in r.json()['products']:
        all_products[p['sku_id']] = p

def find_by_kw(category, keywords, exclude_skus=None):
    """Find products matching ANY keyword, sorted by match count"""
    exclude_skus = set(exclude_skus or [])
    scored = []
    for sku, p in all_products.items():
        if p['category'] != category: continue
        if sku in exclude_skus: continue
        score = 0
        haystack = (p['name'] or '') + (p.get('ingredients') or '') + (p.get('scene_tags') or '')
        for kw in keywords:
            if kw in haystack: score += 1
        if score > 0:
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored]

def pick_by_sku(skus):
    """Pick specific SKUs"""
    result = []
    for s in skus:
        if s in all_products:
            result.append(all_products[s])
    return result

def build_bundle(ctype, core_kw, side_kw, sachet=False):
    """Build a 2+2+1 bundle for a constitution type"""
    products = []
    used_skus = set()

    # Core products: search across bread + tea + snack
    for cat in ['面包类', '茶饮类', '零食类']:
        matches = find_by_kw(cat, core_kw, used_skus)
        for p in matches[:2]:  # take up to 2 per category
            if p['sku_id'] not in used_skus:
                products.append(p)
                used_skus.add(p['sku_id'])
                break

    # Side products: complementary categories
    for cat in ['零食类', '面包类', '茶饮类']:
        matches = find_by_kw(cat, side_kw, used_skus)
        for p in matches[:2]:
            if p['sku_id'] not in used_skus:
                products.append(p)
                used_skus.add(p['sku_id'])
                break

    # Fill up to 6 minimum with more products from any category
    if len(products) < 6:
        for cat in ['面包类', '零食类', '茶饮类', '香囊类']:
            remaining = [p for s, p in all_products.items()
                        if p['category'] == cat and p['sku_id'] not in used_skus]
            for p in remaining[:1]:
                products.append(p)
                used_skus.add(p['sku_id'])
                if len(products) >= 6:
                    break
            if len(products) >= 6:
                break

    # Delight: add a sachet if relevant
    if sachet:
        sachets = find_by_kw('香囊类', ['安神', '玫瑰', '檀香', '暖', '薰衣'], used_skus)
        if sachets:
            products.append(sachets[0])
            used_skus.add(sachets[0]['sku_id'])

    return products

# ── 10 Constitution Bundles ──
BUNDLES = {
    "气虚质": {
        "desc": "气虚体质常感疲劳乏力、气短懒言、易出汗。推荐补气健脾产品，黄芪、山药、茯苓为核心。",
        "core": ["黄芪", "山药", "茯苓", "人参", "芡实", "莲子"],
        "side": ["红枣", "桂圆", "核桃", "枸杞", "薏仁"],
    },
    "阳虚质": {
        "desc": "阳虚体质畏寒怕冷、手足不温、喜热饮食。推荐温阳益气产品，肉桂、干姜、核桃为核心。",
        "core": ["肉桂", "姜", "核桃", "黄芪", "杜仲", "肉苁蓉"],
        "side": ["黑芝麻", "枸杞", "桂圆", "红枣", "山药"],
    },
    "阴虚质": {
        "desc": "阴虚体质口燥咽干、手足心热、盗汗便干。推荐滋阴润燥产品，百合、玉竹、石斛为核心。",
        "core": ["百合", "玉竹", "石斛", "麦冬", "银耳", "枸杞"],
        "side": ["桑葚", "黑芝麻", "山药", "葛根", "芦根"],
    },
    "血虚质": {
        "desc": "血虚体质面色苍白或萎黄、头晕心悸、失眠多梦。推荐补血养心产品，红枣、桂圆、当归为核心。",
        "core": ["红枣", "桂圆", "当归", "枸杞", "桑葚", "黑芝麻"],
        "side": ["核桃", "山药", "茯苓", "酸枣仁"],
    },
    "痰湿质": {
        "desc": "痰湿体质体型偏胖、腹部肥满、口黏苔腻。推荐化痰祛湿产品，薏仁、茯苓、陈皮为核心。",
        "core": ["薏仁", "茯苓", "陈皮", "赤小豆", "冬瓜", "荷叶"],
        "side": ["山楂", "山药", "鸡内金", "决明子", "白扁豆"],
    },
    "湿热质": {
        "desc": "湿热体质面垢油光、口苦口干、易生痤疮。推荐清热利湿产品，菊花、金银花、薏仁为核心。",
        "core": ["菊花", "金银花", "薏仁", "绿豆", "决明子", "蒲公英"],
        "side": ["荷叶", "茯苓", "陈皮", "山楂", "葛根"],
    },
    "血瘀质": {
        "desc": "血瘀体质肤色晦暗、容易出现瘀斑、疼痛固定。推荐活血化瘀产品，山楂、桃仁、红花为核心。",
        "core": ["山楂", "桃仁", "红花", "丹参", "黑芝麻", "玫瑰"],
        "side": ["核桃", "枸杞", "山药", "葛根"],
    },
    "气郁质": {
        "desc": "气郁体质神情抑郁、忧虑脆弱、胸闷叹气。推荐疏肝理气产品，玫瑰、佛手、陈皮为核心。",
        "core": ["玫瑰", "佛手", "陈皮", "茉莉", "合欢", "薄荷"],
        "side": ["山楂", "枸杞", "百合", "酸枣仁"],
        "sachet": True,
    },
    "特禀质": {
        "desc": "特禀体质容易过敏、打喷嚏、鼻炎哮喘。推荐固表益气产品，黄芪、白术、防风为核心。",
        "core": ["黄芪", "白术", "防风", "灵芝", "山药"],
        "side": ["百合", "枸杞", "红枣", "核桃"],
    },
    "平和质": {
        "desc": "平和体质阴阳调和，是理想的健康状态。推荐日常食养维护，均衡搭配各类产品。",
        "core": ["全麦", "枸杞", "核桃", "红枣", "山药"],
        "side": ["黑芝麻", "玫瑰", "高纤", "杂粮"],
    },
}

for ctype, config in BUNDLES.items():
    products = build_bundle(ctype, config["core"], config["side"], config.get("sachet", False))

    print(f"\n{ctype}: {len(products)} products")
    for i, p in enumerate(products):
        role = "核心" if i < 2 else "搭配" if i < 4 else "锦上添花" if i >= len(products)-1 else "补充"
        print(f"  [{role}] {p['name'][:25]} ({p['sku_id']})")

    payload = {
        "products": [
            {"sku_id": p['sku_id'], "sort_order": i, "description": config['desc']}
            for i, p in enumerate(products)
        ]
    }
    r = requests.put(f"{BASE}/api/staff/constitution-bundles/{ctype}", json=payload)
    print(f"  => {'OK' if r.status_code == 200 else 'FAIL '+str(r.status_code)}: {len(products)} products")

print(f"\n{'='*50}")
print("ALL 10 CONSTITUTION BUNDLES CONFIGURED")
