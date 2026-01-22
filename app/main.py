import logging
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db
from app.api.v1.router import api_router
from app.schemas.response import HealthResponse
from app.middleware.logging import LoggingMiddleware

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="NYC Real Estate Zoning Platform API",
    description="API for analyzing NYC property zoning and development potential",
    version="1.0.0"
)

# Logging middleware (before CORS to log all requests)
app.add_middleware(LoggingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    Checks database connectivity and PostGIS availability.
    """
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_status = "connected"
        
        # Check PostGIS version
        result = db.execute(text("SELECT PostGIS_Version()"))
        postgis_version = result.scalar()
    except Exception as e:
        db_status = f"error: {str(e)}"
        postgis_version = None
    
    return HealthResponse(
        status="healthy",
        database=db_status,
        postgis_version=postgis_version
    )


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "NYC Real Estate Zoning Platform API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
