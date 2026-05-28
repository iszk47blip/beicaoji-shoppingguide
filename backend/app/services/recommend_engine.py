# backend/app/services/recommend_engine.py
import re
import json
from app.services.product_service import ProductService
from app.services.constitution_analyzer import analyze


class RecommendEngine:
    def __init__(self, product_service: ProductService, client=None, screening_result: str = ""):
        self.product_service = product_service
        self.client = client
        self.screening_result = screening_result or ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def recommend(self, constitution_raw: str, scene_input: str, constitution_type: str = None) -> dict:
        if constitution_type:
            constitution = {"constitution_type": constitution_type, "description": "", "avoid_tags": [], "prefer_tags": [], "score": 0, "all_scores": {}}
        else:
            constitution = analyze(constitution_raw)
        ctype = constitution.get("constitution_type", "平和质")

        # Step 1: Fixed bundle from DB (all items, no limit)
        fixed_bundle = self._get_fixed_bundle(ctype)
        fixed_skus = {p.sku_id for p in fixed_bundle}

        # Step 2: Tag-based matching (direct + AI)
        tag_matched = self._match_by_tags(scene_input, fixed_skus)

        # Step 3: Contraindication filter
        fixed_bundle, tag_matched = self._filter_contraindications(
            fixed_bundle, tag_matched, self.screening_result
        )

        def _to_dict(p):
            if isinstance(p, dict):
                return p
            return {"name": p.name, "sku_id": p.sku_id, "category": p.category,
                    "ingredients": p.ingredients or "", "price": p.price or 0}

        fixed_dicts = [_to_dict(p) for p in fixed_bundle]
        llm_dicts = [_to_dict(p) for p in tag_matched]
        no_match = len(fixed_bundle) == 0 and len(tag_matched) == 0

        return {
            "constitution": constitution,
            "bundle": fixed_dicts + llm_dicts,
            "fixed_bundle": fixed_dicts,
            "llm_recommendations": llm_dicts,
            "no_match": no_match,
        }

    # ------------------------------------------------------------------
    # Fixed bundle (from DB)
    # ------------------------------------------------------------------

    def _get_fixed_bundle(self, constitution_type: str) -> list:
        """Load all fixed bundle products for this constitution type."""
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
    # Two-layer tag matching
    # ------------------------------------------------------------------

    def _match_by_tags(self, scene_input: str, exclude_skus: set) -> list:
        """Layer 1: direct keyword match + Layer 2: AI semantic match."""
        if not scene_input:
            return []

        from app.models.product import Product
        EDIBLE_CATEGORIES = {"面包类", "茶饮类", "零食类", "面团类", "香囊类", "现场冲泡茶饮"}
        all_products = self.product_service.session.query(Product).filter(
            Product.is_active == True, Product.stock > 0,
            Product.category.in_(EDIBLE_CATEGORIES)
        ).all()

        exclude_skus = set(exclude_skus)
        matched = []  # (score, product, source)
        seen = set()

        # Layer 1: direct word match from customer's own words
        direct_words = self._extract_words(scene_input)
        for p in all_products:
            if p.sku_id in exclude_skus:
                continue
            tags = (p.scene_tags or "").replace("，", ",")
            score = sum(1 for w in direct_words if w in tags)
            if score > 0 and p.sku_id not in seen:
                matched.append((score + 10, p, "direct"))  # +10 bonus for direct match
                seen.add(p.sku_id)

        # Layer 2: AI semantic expansion
        if self.client and len(matched) < 4:
            ai_keywords = self._ai_extract_keywords(scene_input)
            for p in all_products:
                if p.sku_id in exclude_skus or p.sku_id in seen:
                    continue
                tags = (p.scene_tags or "").replace("，", ",")
                score = sum(1 for kw in ai_keywords if kw in tags)
                if score > 0:
                    matched.append((score, p, "ai"))
                    seen.add(p.sku_id)

        # Sort by score desc, take up to 4
        matched.sort(key=lambda x: -x[0])
        return [p for _, p, _ in matched[:4]]

    def _extract_words(self, text: str) -> list:
        """Extract meaningful 2-char+ words from customer text."""
        stops = {"的", "了", "是", "我", "不", "也", "都", "就", "有", "在", "和", "很", "要", "会", "吗", "呢", "吧"}
        words = []
        for i in range(len(text) - 1):
            for j in range(i + 2, min(i + 5, len(text) + 1)):
                w = text[i:j]
                if w not in stops and w not in words:
                    words.append(w)
        return words

    def _ai_extract_keywords(self, scene_input: str) -> list:
        """LLM: extract both colloquial and TCM keywords from customer concern."""
        if not self.client:
            return []
        from app.config import settings
        try:
            prompt = (
                f"顾客困扰：「{scene_input}」\n\n"
                "请提取3-5个关键词用于匹配产品标签。同时输出口语和术语。\n"
                "只输出关键词，用逗号分隔，不要解释。\n\n"
                "示例：顾客说\"睡眠不好\" → 睡眠,失眠,安神,助眠,盗汗"
            )
            resp = self.client.messages.create(
                model=settings.llm_model, max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            )
            text = ""
            for block in resp.content:
                if hasattr(block, "text") and block.text.strip():
                    text = block.text.strip()
                    break
            return [kw.strip() for kw in text.replace("，", ",").split(",") if kw.strip()]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Contraindication filter
    # ------------------------------------------------------------------

    def _filter_contraindications(self, fixed_bundle: list, tag_matched: list, screening: str) -> tuple:
        """Filter out products whose contraindication_tags match screening risks."""
        if not screening or screening == "cleared":
            return fixed_bundle, tag_matched

        risk_map = {
            "备孕": ["孕妇", "备孕", "怀孕"],
            "怀孕": ["孕妇", "备孕", "怀孕"],
            "哺乳": ["哺乳", "孕妇"],
            "处方药": ["药物", "处方"],
            "blocked": ["孕妇", "备孕", "哺乳", "药物", "处方"],
            "downgraded": ["孕妇", "备孕"],
        }

        risks = set()
        for key, values in risk_map.items():
            if key in screening:
                risks.update(values)

        if not risks:
            return fixed_bundle, tag_matched

        def is_safe(product):
            contra = (product.contraindication_tags or "").replace("，", ",")
            for risk in risks:
                if risk in contra:
                    return False
            return True

        return [p for p in fixed_bundle if is_safe(p)], [p for p in tag_matched if is_safe(p)]
