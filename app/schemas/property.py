from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from app.models.property import Borough


class ZoningDistrictInfo(BaseModel):
    """Zoning district information in API responses."""
    code: str
    type: str
    is_primary: bool = False


class NearbyLandmarkInfo(BaseModel):
    """Nearby landmark information in API responses."""
    name: str
    landmark_type: str
    distance_feet: float


class PropertyResponse(BaseModel):
    """Property response schema."""
    id: UUID
    bbl: str
    address: Optional[str] = None
    borough: str
    block: int
    lot: int
    land_area: Optional[float] = None
    year_built: Optional[int] = None
    num_floors: Optional[int] = None
    units_res: Optional[int] = None
    units_total: Optional[int] = None
    assessed_value: Optional[float] = None
    zoning_districts: List[ZoningDistrictInfo] = []
    nearby_landmarks: List[NearbyLandmarkInfo] = []
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PropertyLookupQuery(BaseModel):
    """Query parameters for property lookup."""
    address: Optional[str] = Field(None, description="Property address")
    bbl: Optional[str] = Field(None, description="BBL (Borough-Block-Lot)")
    lat: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    lon: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")
    
    def validate(self):
        """Validate that at least one lookup parameter is provided."""
        if not any([self.address, self.bbl, (self.lat and self.lon)]):
            raise ValueError("At least one of address, bbl, or lat/lon must be provided")
        return self
