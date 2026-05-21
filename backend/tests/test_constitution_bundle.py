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
    assert result[0].sku_id == "S001"


def test_constitution_bundle_unique_constraint(test_db):
    from sqlalchemy.exc import IntegrityError
    item1 = ConstitutionBundle(constitution_type="气虚质", sku_id="S001", sort_order=0)
    test_db.add(item1)
    test_db.commit()
    item2 = ConstitutionBundle(constitution_type="气虚质", sku_id="S001", sort_order=1)
    test_db.add(item2)
    try:
        test_db.commit()
        assert False, "Should have raised IntegrityError"
    except Exception:
        test_db.rollback()