from sqlalchemy import Column, String, Date, Index, Enum as SQLEnum
from geoalchemy2 import Geometry
import enum

from app.models.base import BaseModel


class LandmarkType(str, enum.Enum):
    """Landmark designation type enumeration."""
    INDIVIDUAL = "Individual"
    HISTORIC_DISTRICT = "Historic District"
    SCENIC = "Scenic"


class Landmark(BaseModel):
    """Landmark model representing NYC landmarks and historic districts."""
    
    __tablename__ = "landmarks"
    
    # Landmark information
    name = Column(String(500), nullable=False)
    landmark_type = Column(SQLEnum(LandmarkType), nullable=False)
    designation_date = Column(Date, nullable=True)
    
    # PostGIS geometry (polygon for districts, point/polygon for individual landmarks)
    geometry = Column(
        Geometry(geometry_type='GEOMETRY', srid=4326),
        nullable=False
    )
    
    # Spatial index on geometry column
    __table_args__ = (
        Index('idx_landmarks_geometry', geometry, postgresql_using='gist'),
    )
