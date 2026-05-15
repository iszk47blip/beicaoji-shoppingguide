from app.models.product import Product
from app.services.constitution_analyzer import CONSTITUTION_RULES


class ProductService:
    def __init__(self, session):
        self.session = session

    def search(self, scene_tags=None, exclude_tags=None, categories=None, limit=20):
        q = self.session.query(Product).filter(Product.is_active == True)
        if categories:
            q = q.filter(Product.category.in_(categories))
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
        q = self.session.query(Product).filter(Product.is_active == True)
        if category:
            q = q.filter(Product.category == category)
        return q.all()

    def get_constitution_catalog(self) -> list[dict]:
        """为每种体质生成跨品类产品套餐，基于成分关键词匹配。"""
        # 体质→食养成分关键词映射
        CONSTITUTION_INGREDIENTS = {
            "气虚质": ["山药", "茯苓", "莲子", "薏仁", "小米", "红枣", "黄芪", "党参", "白扁豆"],
            "阳虚质": ["肉桂", "干姜", "枸杞", "桂圆", "核桃", "生姜", "花椒", "小茴香"],
            "阴虚质": ["百合", "银耳", "知母", "麦冬", "枸杞", "桑葚", "玉竹", "生地"],
            "湿热质": ["薏仁", "茯苓", "赤小豆", "绿豆", "陈皮", "苦瓜", "冬瓜", "荷叶"],
        }

        catalog = []
        all_products = self.get_all_active()

        for ctype, rules in CONSTITUTION_RULES.items():
            if ctype == "平和质":
                continue
            keywords = CONSTITUTION_INGREDIENTS.get(ctype, [])
            # 按成分关键词匹配
            matched = [
                p for p in all_products
                if p.ingredients and any(k in p.ingredients for k in keywords)
            ]
            # 跨品类选品，每品类最多一个
            seen_cats = set()
            bundle = []
            for p in matched:
                if p.category not in seen_cats:
                    bundle.append(p)
                    seen_cats.add(p.category)
                if len(bundle) >= 3:
                    break
            # 如果没有匹配到产品，从所有产品中选（至少保证有内容）
            if not bundle:
                for p in all_products:
                    if p.category not in seen_cats:
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
