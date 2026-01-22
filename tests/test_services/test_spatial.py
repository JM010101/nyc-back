"""
Tests for spatial service.
"""
import pytest
from geoalchemy2 import WKTElement
from shapely.geometry import Point, Polygon

from app.models.property import Property, Borough
from app.models.zoning import ZoningDistrict, ZoningType
from app.models.landmark import Landmark, LandmarkType
from app.services.spatial import SpatialService


@pytest.fixture
def sample_property(db_session):
    """Create a sample property for testing."""
    polygon = Polygon([
        (-74.0059, 40.7128),
        (-74.0050, 40.7128),
        (-74.0050, 40.7135),
        (-74.0059, 40.7135),
        (-74.0059, 40.7128)
    ])
    
    property_obj = Property(
        bbl="1000120001",
        address="123 Test St, Manhattan",
        borough=Borough.MANHATTAN,
        block=1,
        lot=1,
        geometry=WKTElement(polygon.wkt, srid=4326),
        land_area=5000.0
    )
    
    db_session.add(property_obj)
    db_session.commit()
    db_session.refresh(property_obj)
    
    return property_obj


def test_find_property_by_bbl(db_session, sample_property):
    """Test finding property by BBL."""
    service = SpatialService(db_session)
    
    property_obj = service.find_property_by_bbl("1000120001")
    
    assert property_obj is not None
    assert property_obj.bbl == "1000120001"


def test_find_property_by_bbl_not_found(db_session):
    """Test finding property by BBL that doesn't exist."""
    service = SpatialService(db_session)
    
    property_obj = service.find_property_by_bbl("9999999999")
    
    assert property_obj is None


def test_find_property_by_coordinates(db_session, sample_property):
    """Test finding property by coordinates."""
    service = SpatialService(db_session)
    
    # Point inside the property polygon
    property_obj = service.find_property_by_coordinates(40.7130, -74.0055)
    
    assert property_obj is not None
    assert property_obj.bbl == sample_property.bbl


def test_find_nearby_landmarks(db_session, sample_property):
    """Test finding nearby landmarks."""
    # Create a landmark close to the property
    point = Point(-74.0055, 40.7130)  # Inside property polygon
    landmark = Landmark(
        name="Nearby Landmark",
        landmark_type=LandmarkType.INDIVIDUAL,
        geometry=WKTElement(point.wkt, srid=4326)
    )
    db_session.add(landmark)
    db_session.commit()
    
    service = SpatialService(db_session)
    landmarks = service.find_nearby_landmarks(sample_property.geometry, distance_feet=150.0)
    
    assert len(landmarks) > 0
    assert any(lm.name == "Nearby Landmark" for lm, _ in landmarks)
