# backend/tests/conftest.py
import pytest
from app.models import Base
from app.services.data_importer import import_all


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


@pytest.fixture
def test_db_with_products(test_db):
    import_all(test_db)
    # Set stock > 0 so recommend engine filters work
    from app.models.product import Product
    test_db.query(Product).update({Product.stock: 10})
    test_db.commit()
    return test_db