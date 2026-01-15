"""
SCET - Smart Copyright Expiry Tag System
Main FastAPI Application
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import asyncio

from .api.routes import router
from .database.connection import init_db
from .data_collection.scheduler import get_scheduler
from .ml_model.trainer import get_trainer
from .config import get_settings

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    # Startup
    logger.info("Starting SCET System...")
    
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    
    # Bootstrap ML model if needed
    trainer = get_trainer()
    if trainer.predictor.get_model_stats().get('training_samples', 0) == 0:
        logger.info("Bootstrapping ML model with initial training data...")
        await trainer.bootstrap_model()
    
    # Start data update scheduler
    if not settings.DEBUG:
        scheduler = get_scheduler()
        await scheduler.start()
        logger.info("Data update scheduler started")
    
    logger.info("SCET System started successfully!")
    
    yield
    
    # Shutdown
    logger.info("Shutting down SCET System...")
    
    scheduler = get_scheduler()
    await scheduler.stop()
    
    logger.info("SCET System shutdown complete")


# OpenAPI tag descriptions
tags_metadata = [
    {
        "name": "System",
        "description": "Health checks and system statistics endpoints.",
    },
    {
        "name": "Search",
        "description": "AI-powered title search with spell correction, fuzzy matching, and semantic similarity.",
    },
    {
        "name": "Analysis",
        "description": "Detailed copyright analysis with legal reasoning and ML predictions.",
    },
    {
        "name": "Smart Tag",
        "description": "Generate human-readable Smart Copyright Expiry Tags with confidence scoring.",
    },
    {
        "name": "Data Collection",
        "description": "Manage live web scraping and data collection from external sources.",
    },
    {
        "name": "ML Model",
        "description": "Machine learning model status, training, and feedback endpoints.",
    },
    {
        "name": "Works",
        "description": "Access and manage the works metadata database.",
    },
    {
        "name": "Jurisdictions",
        "description": "Copyright rules and information for different jurisdictions.",
    },
]

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="""
# 🏷️ SCET - Smart Copyright Expiry Tag

**AI-Based Title Search and Self-Updating ML Model**

A research-grade AI system for determining copyright ownership, permissions, and expiry.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🔍 **AI Title Search** | Spell correction, fuzzy matching, semantic similarity |
| 🌐 **Live Data Collection** | Scrapes Open Library, Wikipedia, MusicBrainz, IMDb |
| 🤖 **ML Prediction** | Self-learning model that improves with usage |
| 🏷️ **Smart Tags** | Human-readable copyright status with emojis |
| 🌍 **Multi-Jurisdiction** | US, EU, UK, Canada, Australia, Japan, India |

---

## 🎯 Quick Start

1. **Search for a work**: `POST /api/v1/search` with a title
2. **Get Smart Tag**: `POST /api/v1/tag` for human-readable copyright info
3. **Analyze copyright**: `POST /api/v1/analyze` for detailed legal analysis

---

## 📜 Novelty Statement

> *This system does not rely on pre-existing datasets. It uses AI-based live data acquisition 
> and machine learning to dynamically infer copyright status and expiry.*

---

⚠️ **Disclaimer**: This tool is for educational purposes only and does not constitute legal advice.
    """,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=tags_metadata,
    contact={
        "name": "SCET Research Project",
        "url": "https://github.com/scet-project",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    }
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred",
            "code": "INTERNAL_ERROR"
        }
    )


# Include API routes
app.include_router(router, prefix=settings.API_PREFIX)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": "Smart Copyright Expiry Tag with AI-Based Title Search",
        "docs": "/docs",
        "api_prefix": settings.API_PREFIX,
        "features": [
            "AI-powered title search with spell correction",
            "Live data collection from web sources",
            "ML-based copyright prediction",
            "Smart copyright expiry tags",
            "Multi-jurisdiction support"
        ]
    }


# Quick search endpoint at root level for convenience
@app.get("/search")
async def root_search(q: str):
    """Quick search redirect"""
    return {
        "message": f"Use {settings.API_PREFIX}/search?q={q} for full search",
        "redirect": f"{settings.API_PREFIX}/search?q={q}"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
