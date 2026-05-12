from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.chat import router as chat_router
from app.api.admin import router as admin_router
from app.api.staff import router as staff_router

app = FastAPI(title="焙草集AI助手API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(chat_router)
app.include_router(admin_router)
app.include_router(staff_router)


@app.get("/health")
def health():
    return {"status": "ok"}