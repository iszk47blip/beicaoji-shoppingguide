# backend/tests/test_constitution_bundle.py
from app.models.constitution_bundle import ConstitutionBundle, HotProduct

def test_constitution_bundle_crud(test_db):
    item = ConstitutionBundle(constitution_type="气虚质", sku_id="S001", sort_order=0)
    test_db.add(item)
    test_db.commit()
    result = test_db.query(ConstitutionBundle).filter_by(constitution_type="气虚质").all()
    assert len(result) == 1
    assert result[0].sku_id == "S001"

def test_hot_product_crud(test_db):
    item = HotProduct(sku_id="S001", sort_order=0)
    test_db.add(item)
    test_db.commit()
    result = test_db.query(HotProduct).all()
    assert len(result) == 1