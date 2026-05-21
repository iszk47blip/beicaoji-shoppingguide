from fastapi import APIRouter, Response
from pathlib import Path

router = APIRouter(prefix="/orders", tags=["orders"])

_ORDERS_HTML = Path(__file__).parent.parent / "orders.html"


@router.get("")
def serve_orders():
    return Response(_ORDERS_HTML.read_text(encoding="utf-8"), media_type="text/html")