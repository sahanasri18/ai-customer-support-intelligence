"""
FastAPI application entry point.
"""
import logging
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.orm import Session

from config import settings
from database import get_db
import models  # noqa: F401 — register all ORM models with Base
from routers import auth_router, users_router, tickets_router, analytics_router, predictions_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API startup complete. Initialize the database with database/schema.sql.")
    yield


app = FastAPI(
    title="AI Customer Support Intelligence Platform",
    description="REST API for customer support ticket management with ML predictions.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(tickets_router.router)
app.include_router(analytics_router.router)
app.include_router(predictions_router.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/health/database")
def database_health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "reachable"}
    except Exception:
        logger.exception("Database health check failed")
        raise HTTPException(status_code=503, detail="Database unavailable")
