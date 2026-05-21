from fastapi import APIRouter, Response
from pathlib import Path

router = APIRouter(prefix="/staff-admin", tags=["staff-admin"])

_ADMIN_HTML = Path(__file__).parent.parent / "staff-admin.html"


@router.get("")
def serve_staff_admin():
    return Response(_ADMIN_HTML.read_text(encoding="utf-8"), media_type="text/html")