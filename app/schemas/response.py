from pydantic import BaseModel
from typing import Optional, Any
from app.schemas.property import PropertyResponse


class PropertyLookupResponse(BaseModel):
    """Response schema for property lookup endpoint."""
    property: Optional[PropertyResponse] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str
    database: str
    postgis_version: Optional[str] = None
