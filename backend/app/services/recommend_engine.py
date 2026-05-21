# backend/app/services/recommend_engine.py
import random
import re
import json
from datetime import datetime
from app.services.product_service import ProductService
from app.services.constitution_analyzer import analyze

SCENE_TAG_MAP = {
    "睡": ["睡眠", "安神", "助眠"],
    "消化": ["消食", "健脾", "肠胃"],
    "胃": ["消食", "健脾", "肠胃"],
    "累": ["补气", "抗疲劳", "精力"],
    "疲劳": ["补气", "抗疲劳", "精力"],
    "皮肤": ["养颜", "润肤", "安神", "清热"],
    "上火": ["清热", "降火"],
    "心情": ["安神", "舒缓", "助眠"],
    "压力": ["安神", "舒缓", "补气"],
    "调理": ["补气", "健脾", "滋阴", "温补"],
    "湿": ["利湿", "健脾", "清热"],
    "寒": ["温补", "暖身", "补气"],
    "免疫": ["补气", "抗疲劳", "温补"],
    "头发": ["养颜", "补气", "滋阴"],
    "气色": ["养颜", "补气", "滋阴"],
    "经期": ["温补", "暖身", "舒缓"],
}

class RecommendEngine:
    def __init__(self, product_service: ProductService, client=None):
        self.product_service = product_service
        self.client = client  # LLM client, injected from chat.py

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def recommend(self, constitution_raw: str, scene_input: str) -> dict:
        constitution = analyze(constitution_raw)
        scene_tags = self._extract_scene_tags(scene_input)
        constitution_type = constitution.get("constitution_type", "平和质")

        # Get fixed bundle from DB
        fixed_bundle = self._get_fixed_bundle(constitution_type)
        fixed_skus = {p.sku_id for p in fixed_bundle}

        # Get LLM supplement (excluding fixed_skus)
        llm_products = self._llm_supplement(list(fixed_skus), constitution_type, scene_input)

        def _to_dict(p):
            if isinstance(p, dict):
                return p
            return {"name": p.name, "sku_id": p.sku_id, "category": p.category,
                    "ingredients": p.ingredients or "", "price": p.price or 0}

        no_match = len(fixed_bundle) == 0 and len(llm_products) == 0

        return {
            "constitution": constitution,
            "scene_tags": scene_tags,
            "fixed_bundle": [_to_dict(p) for p in fixed_bundle],
            "llm_recommendations": [_to_dict(p) for p in llm_products],
            "no_match": no_match,
        }

    # ------------------------------------------------------------------
    # Scene tags
    # ------------------------------------------------------------------

    def _extract_scene_tags(self, scene_input):
        tags = []
        for keyword, mapped_tags in SCENE_TAG_MAP.items():
            if keyword in scene_input:
                tags.extend(mapped_tags)
        return list(set(tags)) if tags else ["调理"]

    # ------------------------------------------------------------------
    # Fixed bundle (from DB)
    # ------------------------------------------------------------------

    def _get_fixed_bundle(self, constitution_type: str) -> list:
        """Load fixed bundle from DB for this constitution type."""
        from app.models.constitution_bundle import ConstitutionBundle
        items = self.product_service.session.query(ConstitutionBundle).filter(
            ConstitutionBundle.constitution_type == constitution_type
        ).order_by(ConstitutionBundle.sort_order).all()
        products = []
        for item in items:
            product = self.product_service.get_by_sku(item.sku_id)
            if product and product.is_active and product.stock > 0:
                products.append(product)
        return products

    # ------------------------------------------------------------------
    # LLM supplement
    # ------------------------------------------------------------------

    def _llm_supplement(self, fixed_skus: list, constitution_type: str, scene_input: str) -> list:
        """Use LLM to suggest supplementary products based on customer context, excluding fixed_skus."""
        if not self.client:
            return []

        from app.config import settings
        fixed_names = []
        for s in fixed_skus:
            p = self.product_service.get_by_sku(s)
            if p:
                fixed_names.append(p.name)

        prompt = (
            f"顾客体质：{constitution_type}。\n"
            f"当前困扰：{scene_input}\n"
            f"固定套餐已有：{', '.join(fixed_names) if fixed_names else '无'}\n\n"
            "请根据顾客体质和困扰，推荐2~4款店里可能有的产品（只推荐食品类，不要手串/香囊/玩具）。\n"
            "返回JSON数组，每项格式：{\"name\": \"产品名\", \"sku_id\": \"条码\", \"reason\": \"推荐原因\"}\n"
            "只推荐你确定店里有的产品，不要编造。"
        )
        try:
            resp = self.client.messages.create(
                model=settings.llm_model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )
            text = ""
            for block in resp.content:
                if hasattr(block, "text") and block.text.strip():
                    text = block.text.strip()
                    break
            if not text:
                return []
            m = re.search(r'\[.*\]', text, re.DOTALL)
            if not m:
                return []
            items = json.loads(m.group(0))
        except Exception:
            return []

        # Fetch full product objects, exclude fixed_skus
        result = []
        for item in items[:4]:
            sku = item.get("sku_id", "")
            if sku and sku not in fixed_skus:
                product = self.product_service.get_by_sku(sku)
                if product and product.is_active and product.stock > 0:
                    result.append(product)
        return result
