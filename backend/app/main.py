import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler
from app.api.chat import router as chat_router
from app.api.admin import router as admin_router
from app.api.staff import router as staff_router
from app.api.report_page import router as report_page_router
from app.api.staff_admin import router as staff_admin_router
from app.api.orders_page import router as orders_page_router
from app.api.reports import router as reports_router
from app.api.auth import router as auth_router
from app.config import settings
from app.models import get_session

logger = logging.getLogger("uvicorn")

_scheduler = None


def _run_auto_review():
    """Background task: auto-review recent conversations."""
    try:
        from app.services.review_service import ReviewService
        db = get_session()
        try:
            svc = ReviewService()
            # Convert hours to days fraction for the review window
            window_days = max(settings.auto_review_interval_hours / 24.0, 0.04)  # min ~1 hour
            result = svc.review_conversations(db, days=window_days)
            if result.get("reviewed", 0) > 0:
                logger.info(
                    f"[auto-review] 审核完成: {result['reviewed']} 条对话, "
                    f"评分 {result.get('quality_score', '?')}, "
                    f"问题 {len(result.get('problems_found', []))} 个"
                )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[auto-review] 审核失败: {e}")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global _scheduler
    if settings.auto_review_enabled:
        _scheduler = BackgroundScheduler()
        _scheduler.add_job(
            _run_auto_review,
            trigger="interval",
            hours=settings.auto_review_interval_hours,
            id="auto_review",
        )
        _scheduler.start()
        logger.info(
            f"[auto-review] 已启动, 每 {settings.auto_review_interval_hours} 小时自动审核"
        )
        # Run first review immediately (5s delay for server to be ready)
        import threading
        threading.Timer(5, _run_auto_review).start()
    yield
    if _scheduler:
        _scheduler.shutdown(wait=False)


app = FastAPI(title="焙草集AI助手API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(chat_router)
app.include_router(admin_router)
app.include_router(staff_router)
app.include_router(report_page_router)
app.include_router(staff_admin_router)
app.include_router(orders_page_router)
app.include_router(reports_router)
app.include_router(auth_router)

# Serve login page
_LOGIN_HTML = Path(__file__).parent / "login.html"

# Serve static files (youzan QR code, etc.)
_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# Serve test page at root
_TEST_HTML = Path(__file__).parent.parent.parent / "test-chat.html"


@app.get("/")
def serve_test_page():
    if _TEST_HTML.exists():
        return HTMLResponse(
            _TEST_HTML.read_text(encoding="utf-8"),
            headers={
                "Cache-Control": "no-store, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/login")
def serve_login():
    if _LOGIN_HTML.exists():
        return HTMLResponse(
            _LOGIN_HTML.read_text(encoding="utf-8"),
            headers={"Cache-Control": "no-store, must-revalidate, max-age=0", "Pragma": "no-cache", "Expires": "0"},
        )
    return HTMLResponse("<h1>Login page not found</h1>", status_code=404)