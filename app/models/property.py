from sqlalchemy import Column, String, Integer, Numeric, ARRAY, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
import enum

from app.models.base import BaseModel
from app.database import Base


class Borough(str, enum.Enum):
    """NYC Borough enumeration."""
    MANHATTAN = "Manhattan"
    BROOKLYN = "Brooklyn"
    QUEENS = "Queens"
    BRONX = "Bronx"
    STATEN_ISLAND = "Staten Island"


class Property(BaseModel):
    """Property/MapPLUTO model representing NYC property parcels."""
    
    __tablename__ = "properties"
    
    # BBL (Borough-Block-Lot) - unique identifier
    bbl = Column(String(10), unique=True, nullable=False, index=True)
    
    # Address information
    address = Column(String(255), nullable=True, index=True)
    borough = Column(SQLEnum(Borough), nullable=False)
    block = Column(Integer, nullable=False)
    lot = Column(Integer, nullable=False)
    
    # PostGIS geometry (polygon representing property boundary)
    geometry = Column(
        Geometry(geometry_type='POLYGON', srid=4326),
        nullable=False
    )
    
    # Property characteristics
    land_area = Column(Numeric(12, 2), nullable=True)  # square feet
    year_built = Column(Integer, nullable=True)
    num_floors = Column(Integer, nullable=True)
    units_res = Column(Integer, nullable=True)  # residential units
    units_total = Column(Integer, nullable=True)
    assessed_value = Column(Numeric(15, 2), nullable=True)
    
    # Zoning codes (stored as array for quick lookup)
    zoning_districts = Column(ARRAY(String), nullable=True)
    
    # Relationships
    property_zoning = relationship(
        "PropertyZoning",
        back_populates="property",
        cascade="all, delete-orphan"
    )
    
    # Spatial index on geometry column
    __table_args__ = (
        Index('idx_properties_geometry', geometry, postgresql_using='gist'),
    )
