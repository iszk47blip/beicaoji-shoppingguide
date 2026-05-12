from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.api.chat import router as chat_router
from app.api.admin import router as admin_router
from app.api.staff import router as staff_router
from app.api.report_page import router as report_page_router

app = FastAPI(title="焙草集AI助手API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(chat_router)
app.include_router(admin_router)
app.include_router(staff_router)
app.include_router(report_page_router)

# Serve test page at root
_TEST_HTML = Path(__file__).parent.parent.parent / "test-chat.html"


@app.get("/")
def serve_test_page():
    if _TEST_HTML.exists():
        return HTMLResponse(_TEST_HTML.read_text(encoding="utf-8"))
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}