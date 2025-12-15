from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from app.routes import events, search, images
from app.config import get_settings
import logging
import os

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
app.include_router(images.router, tags=["images"])

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

# Determine base directory
app_dir = os.path.dirname(__file__)
base_dir = os.path.dirname(app_dir)

# Mount static files directory for HTML interface
if os.path.exists(base_dir):
    app.mount("/static", StaticFiles(directory=base_dir), name="static")
    logger.info(f"Static files mounted at {base_dir}")

@app.get("/events")
async def serve_events_page():
    """Serve the events HTML page"""
    events_file = os.path.join(base_dir, "events.html")
    
    if os.path.exists(events_file):
        return FileResponse(events_file, media_type="text/html")
    else:
        logger.error(f"events.html not found at {events_file}")
        return {"error": f"events.html not found at {events_file}"}

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
