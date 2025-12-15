from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.routes import events, search
from app.config import get_settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="AI-powered event aggregator for Sioux Falls metro area"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(events.router, prefix="/api/events", tags=["events"])
app.include_router(search.router, prefix="/api/search", tags=["search"])

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "elasticsearch_host": settings.ELASTICSEARCH_HOST,
        "ollama_host": settings.OLLAMA_HOST
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "title": settings.API_TITLE,
        "version": settings.API_VERSION,
        "docs": "/docs"
    }

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
