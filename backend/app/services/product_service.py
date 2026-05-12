from app.models.product import Product

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
