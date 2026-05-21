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


def test_search_by_scene(test_db):
    from app.services.product_service import ProductService
    import_all(test_db)
    # Set stock > 0 so product_service search filters work
    from app.models.product import Product
    test_db.query(Product).update({Product.stock: 10})
    test_db.commit()
    svc = ProductService(test_db)
    results = svc.search(scene_tags=["睡眠", "安神"])
    assert len(results) > 0
    for r in results:
        assert "睡眠" in r.scene_tags or "安神" in r.scene_tags
