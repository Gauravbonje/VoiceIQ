from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.logging import log


app = FastAPI(
    title="VoiceIQ v2",
    description="AI Audio Intelligence Platform",
    version="2.0.0",
)


# ── CORS (for Streamlit frontend) ──────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────
app.include_router(router)


# ── Startup Event ─────────────────────────────────────────
@app.on_event("startup")
async def startup():
    log.info("VoiceIQ v2 API started")


# ── Health Check ──────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "VoiceIQ",
        "version": "2.0.0",
    }