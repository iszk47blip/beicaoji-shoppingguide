import pytest
from pathlib import Path
from app.models import Base
from app.models.product import Product
from app.services.data_importer import import_all, import_sheet, FILE_MAP


@pytest.fixture
def test_db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_import_all(test_db):
    count = import_all(test_db)
    assert count > 80, f"Expected >80 products, got {count}"
    products = test_db.query(Product).all()
    categories = set(p.category for p in products)
    assert categories == {"biscuit", "bread", "tea", "toy"}, f"Expected all 4 categories, got {categories}"


def test_import_sheet(test_db):
    from app.models import Base
    filepath = Path("E:/VIBE/beicaoji/beicaoji-产品目录/biscuit.xlsx")
    count = import_sheet(test_db, filepath, "biscuit")
    assert count == 11, f"Expected 11 biscuit products, got {count}"
    products = test_db.query(Product).filter_by(category="biscuit").all()
    assert len(products) == 11
    assert all(p.sku_id for p in products)


def test_dynamic_column_mapping():
    """Test that column names map to correct fields regardless of position."""
    from app.services.data_importer import parse_excel_columns
    # Simulate a header row with known column names
    headers = ["条码", "商品名称", "零售价", "一级分类", "成分", "适宜人群", "商品标签", "场景标签", "禁忌标签", "销售话术"]
    field_map = parse_excel_columns(headers)
    # Returns {field_name: column_index}
    assert field_map["sku_id"] == 0
    assert field_map["name"] == 1
    assert field_map["price"] == 2
    assert field_map["category"] == 3
    assert field_map["ingredients"] == 4
    # "商品标签" -> feature_tag (index 6)
    assert field_map["feature_tag"] == 6
    # "场景标签" -> scene_tags (index 7)
    assert field_map["scene_tags"] == 7
    # "禁忌标签" -> contraindication_tags (index 8)
    assert field_map["contraindication_tags"] == 8
    # "销售话术" -> sales_script (index 9)
    assert field_map["sales_script"] == 9