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