# backend/app/services/recommend_engine.py
import random
from app.services.product_service import ProductService
from app.services.constitution_analyzer import analyze

SCENE_TAG_MAP = {
    "睡": ["睡眠", "安神", "助眠"],
    "消化": ["消食", "健脾", "肠胃"],
    "胃": ["消食", "健脾", "肠胃"],
    "累": ["补气", "抗疲劳", "精力"],
    "疲劳": ["补气", "抗疲劳", "精力"],
    "皮肤": ["养颜", "润肤"],
    "上火": ["清热", "降火"],
    "调理": ["补气", "健脾", "滋阴", "温补"],
}

class RecommendEngine:
    def __init__(self, product_service: ProductService):
        self.product_service = product_service

    def recommend(self, constitution_raw: str, scene_input: str) -> dict:
        constitution = analyze(constitution_raw)
        scene_tags = self._extract_scene_tags(scene_input)
        avoid_tags = constitution["avoid_tags"]
        prefer_tags = constitution["prefer_tags"]
        scene_matches = self.product_service.search(scene_tags=scene_tags + prefer_tags)
        safe_matches = [p for p in scene_matches
                        if not any(t in (p.contraindication_tags or "")
                                   for t in avoid_tags)]
        def _to_dict(p):
            if isinstance(p, dict):
                return p
            return {"name": p.name, "sku_id": p.sku_id, "category": p.category,
                    "ingredients": p.ingredients, "price": p.price}

        bundle = self._build_bundle(safe_matches)
        no_match = len(bundle) == 0

        if no_match:
            bundle = self._fallback_bundle()

        return {
            "constitution": constitution,
            "scene_tags": scene_tags,
            "products": [_to_dict(p) for p in safe_matches[:6]],
            "bundle": [_to_dict(p) for p in bundle],
            "no_match": no_match,
        }

    def _extract_scene_tags(self, scene_input):
        tags = []
        for keyword, mapped_tags in SCENE_TAG_MAP.items():
            if keyword in scene_input:
                tags.extend(mapped_tags)
        return list(set(tags)) if tags else ["调理"]

    def _build_bundle(self, products, size=3):
        if len(products) < 2:
            return products
        cats = {}
        for p in products:
            cats.setdefault(p.category, []).append(p)
        bundle = []
        for cat_products in cats.values():
            if len(bundle) < size:
                bundle.append(cat_products[0])
        return bundle[:size]

    def _fallback_bundle(self, size=3):
        """When no products match, return a cross-category selection of all active products."""
        all_products = self.product_service.get_all_active()
        if not all_products:
            return []
        cats = {}
        for p in all_products:
            cats.setdefault(p.category, []).append(p)
        bundle = []
        for cat_products in cats.values():
            if len(bundle) < size:
                bundle.append(cat_products[0])
        return [{"name": p.name, "sku_id": p.sku_id, "category": p.category,
                 "ingredients": p.ingredients, "price": p.price} for p in bundle[:size]]