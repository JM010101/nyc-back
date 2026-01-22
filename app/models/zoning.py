from sqlalchemy import Column, String, Numeric, JSON, Index, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geometry
import enum

from app.models.base import BaseModel


class ZoningType(str, enum.Enum):
    """Zoning district type enumeration."""
    RESIDENTIAL = "Residential"
    COMMERCIAL = "Commercial"
    MANUFACTURING = "Manufacturing"
    MIXED = "Mixed"


class ZoningDistrict(BaseModel):
    """Zoning district model representing NYC zoning districts."""
    
    __tablename__ = "zoning_districts"
    
    # Zoning code (e.g., "R7-2", "C6-2", "M1-5")
    zoning_code = Column(String(20), unique=True, nullable=False, index=True)
    
    # Zoning type
    zoning_type = Column(SQLEnum(ZoningType), nullable=False)
    
    # PostGIS geometry (polygon representing zoning district boundary)
    geometry = Column(
        Geometry(geometry_type='POLYGON', srid=4326),
        nullable=False
    )
    
    # Zoning regulations
    far_residential = Column(Numeric(5, 2), nullable=True)  # Floor Area Ratio
    far_commercial = Column(Numeric(5, 2), nullable=True)
    max_height = Column(Numeric(8, 2), nullable=True)  # feet
    setback_requirements = Column(JSON, nullable=True)  # Flexible schema for setbacks
    
    # Relationships
    property_zoning = relationship(
        "PropertyZoning",
        back_populates="zoning_district",
        cascade="all, delete-orphan"
    )
    
    # Spatial index on geometry column
    __table_args__ = (
        Index('idx_zoning_districts_geometry', geometry, postgresql_using='gist'),
    )


class PropertyZoning(BaseModel):
    """Junction table for many-to-many relationship between properties and zoning districts."""
    
    __tablename__ = "property_zoning"
    
    property_id = Column(
        UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    zoning_district_id = Column(
        UUID(as_uuid=True),
        ForeignKey("zoning_districts.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    is_primary = Column(
        default=False,
        nullable=False
    )  # Is this the primary zoning district?
    
    # Relationships
    property = relationship("Property", back_populates="property_zoning")
    zoning_district = relationship("ZoningDistrict", back_populates="property_zoning")
    
    # Unique constraint to prevent duplicate relationships
    __table_args__ = (
        Index('idx_property_zoning_unique', property_id, zoning_district_id, unique=True),
    )
