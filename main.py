"""
ISO Standards AI Assistant
==========================
Entry point: wires FastAPI app, CORS middleware, and all routers.
"""

import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.client import DeepSeekClient
from app.core.config import DEEPSEEK_MODEL
from app.routers import audit_lens, benchmark, chat, navigator, quiz, utils, discovery, rag

load_dotenv()

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 ISO Standards AI Assistant starting...")
    print(f"📦 DeepSeek Model: {DEEPSEEK_MODEL}")
    port = os.getenv("PORT", 8001)
    print(f"🔗 API Documentation: http://localhost:{port}/docs")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down ISO Standards AI Assistant...")
    await DeepSeekClient.close()

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="ISO Standards AI Assistant API",
    description="DeepSeek API-powered backend for ISO compliance management.",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(discovery.router)
app.include_router(navigator.router)
app.include_router(audit_lens.router)
app.include_router(benchmark.router)
app.include_router(chat.router)
app.include_router(quiz.router)
app.include_router(rag.router)
app.include_router(utils.router)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload, log_level="info")
