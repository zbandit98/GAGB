"""Main FastAPI application module."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import games, odds, news, analysis, parlays
from backend.app.config import get_settings
from backend.app.core.database import Base, engine

# Configure logging
logging.basicConfig(
    level=logging.getLevelName(get_settings().log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create database tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup."""
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")
    yield
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=get_settings().app_name,
    description=get_settings().app_description,
    version=get_settings().app_version,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(games.router, prefix="/api", tags=["games"])
app.include_router(odds.router, prefix="/api", tags=["odds"])
app.include_router(news.router, prefix="/api", tags=["news"])
app.include_router(analysis.router, prefix="/api", tags=["analysis"])
app.include_router(parlays.router, prefix="/api", tags=["parlays"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to the GAGB API",
        "docs": "/docs",
        "version": get_settings().app_version,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=get_settings().api_host,
        port=get_settings().api_port,
        reload=get_settings().debug,
    )
