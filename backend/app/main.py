"""Chessian.AI backend — FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables, engine
from app.routers import games, import_, analysis


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables (dev only). Shutdown: dispose engine."""
    if settings.debug:
        await create_tables()
    yield
    await engine.dispose()


app = FastAPI(
    title="Chessian.AI",
    description="AI-powered chess improvement platform API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(games.router, prefix="/api/games", tags=["games"])
app.include_router(import_.router, prefix="/api/import", tags=["import"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "chessian-backend"}

