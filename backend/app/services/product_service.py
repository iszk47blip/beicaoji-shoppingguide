from app.models.product import Product
from app.services.constitution_analyzer import CONSTITUTION_RULES


class ProductService:
    def __init__(self, session):
        self.session = session

    # Food-only categories — exclude "玩具" (handchains/incense) and "其他" (misc)
    # Include both Chinese names and English keys used by data_importer
    FOOD_CATEGORIES = ["饼干", "面包", "茶", "糕点", "滋补", "礼盒", "零食", "冲调", "蜜饯", "糖果", "肉干", "海味", "坚果", "米面", "杂粮", "油", "调味品", "干货",
                       "biscuit", "bread", "tea"]

    def search(self, scene_tags=None, exclude_tags=None, categories=None, limit=20, food_only=True):
        q = self.session.query(Product).filter(Product.is_active == True, Product.stock > 0)
        if categories:
            q = q.filter(Product.category.in_(categories))
        elif food_only:
            q = q.filter(Product.category.in_(self.FOOD_CATEGORIES))
        results = q.all()

        if scene_tags:
            results = [p for p in results if p.scene_tags and
                       any(t in p.scene_tags for t in scene_tags)]
        if exclude_tags:
            results = [p for p in results if p.contraindication_tags and
                       not any(t in p.contraindication_tags for t in exclude_tags)]

        return results[:limit]

    def get_by_sku(self, sku_id):
        return self.session.query(Product).filter(Product.sku_id == sku_id).first()

    def get_all_active(self, category=None):
        q = self.session.query(Product).filter(Product.is_active == True, Product.stock > 0)
        if category:
            q = q.filter(Product.category == category)
        else:
            q = q.filter(Product.category.in_(self.FOOD_CATEGORIES))
        return q.all()

    def get_constitution_catalog(self) -> list[dict]:
        """Return constitution catalog using admin-configured bundles, with ingredient fallback."""
        from app.models.constitution_bundle import ConstitutionBundle
        from app.services.constitution_analyzer import CONSTITUTION_RULES

        # Fallback ingredient keywords for constitutions without admin bundles
        CONSTITUTION_INGREDIENTS = {
            "气虚质": ["山药", "茯苓", "莲子", "薏仁", "小米", "红枣", "黄芪", "党参", "白扁豆"],
            "阳虚质": ["肉桂", "干姜", "枸杞", "桂圆", "核桃", "生姜", "花椒", "小茴香"],
            "阴虚质": ["百合", "银耳", "知母", "麦冬", "枸杞", "桑葚", "玉竹", "生地"],
            "湿热质": ["薏仁", "茯苓", "赤小豆", "绿豆", "陈皮", "苦瓜", "冬瓜", "荷叶"],
            "痰湿质": ["陈皮", "茯苓", "薏仁", "赤小豆", "山楂", "白扁豆", "砂仁"],
            "气郁质": ["佛手", "玫瑰花", "陈皮", "香橼", "薄荷", "柴胡", "青皮"],
            "血瘀质": ["山楂", "桃仁", "红花", "丹参", "当归", "川芎", "玫瑰花"],
            "血虚质": ["当归", "桂圆", "红枣", "枸杞", "黑芝麻", "桑葚", "阿胶"],
            "特禀质": ["黄芪", "防风", "白术", "百合", "山药", "乌梅", "甘草"],
        }

        catalog = []
        all_products = self.get_all_active()

        for ctype, rules in CONSTITUTION_RULES.items():
            if ctype == "平和质":
                continue

            # ── Layer 1: admin-configured bundles ──
            bundle_items = self.session.query(ConstitutionBundle).filter(
                ConstitutionBundle.constitution_type == ctype
            ).order_by(ConstitutionBundle.sort_order).all()

            bundle = []
            seen_skus = set()
            if bundle_items:
                for item in bundle_items:
                    product = self.get_by_sku(item.sku_id)
                    if product and product.is_active and product.stock > 0 and product.sku_id not in seen_skus:
                        bundle.append(product)
                        seen_skus.add(product.sku_id)

            # ── Layer 2: ingredient matching fallback ──
            if not bundle:
                keywords = CONSTITUTION_INGREDIENTS.get(ctype, [])
                matched = [
                    p for p in all_products
                    if p.ingredients and any(k in p.ingredients for k in keywords) and p.sku_id not in seen_skus
                ]
                seen_cats = set()
                for p in matched:
                    if p.category not in seen_cats:
                        bundle.append(p)
                        seen_cats.add(p.category)
                    if len(bundle) >= 3:
                        break

            # ── Layer 3: any products (last resort) ──
            if not bundle:
                seen_cats = set(p.category for p in bundle)
                for p in all_products:
                    if p.sku_id not in seen_skus and p.category not in seen_cats:
                        bundle.append(p)
                        seen_cats.add(p.category)
                    if len(bundle) >= 3:
                        break

            catalog.append({
                "constitution": ctype,
                "description": rules["description"],
                "products": [
                    {"name": p.name, "sku_id": p.sku_id, "category": p.category,
                     "ingredients": p.ingredients or "", "price": p.price or 0}
                    for p in bundle
                ],
            })
        return catalog

    def get_hot_products(self) -> list:
        """Return hot/focus products for storefront display."""
        from app.models.constitution_bundle import HotProduct
        items = self.session.query(HotProduct).order_by(HotProduct.sort_order).all()
        result = []
        for h in items:
            product = self.get_by_sku(h.sku_id)
            if product and product.is_active and product.stock > 0:
                result.append({
                    "name": product.name, "sku_id": product.sku_id,
                    "category": product.category,
                    "ingredients": product.ingredients or "",
                    "price": product.price or 0
                })
        return result
