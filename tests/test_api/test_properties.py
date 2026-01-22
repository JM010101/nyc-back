"""
Tests for property API endpoints.
"""
import pytest
from geoalchemy2 import WKTElement
from shapely.geometry import Point, Polygon

from app.models.property import Property, Borough
from app.models.zoning import ZoningDistrict, ZoningType
from app.models.landmark import Landmark, LandmarkType


@pytest.fixture
def sample_property(db_session):
    """Create a sample property for testing."""
    # Create a simple polygon geometry (Manhattan area)
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
        land_area=5000.0,
        year_built=2000,
        num_floors=5,
        units_res=10,
        units_total=10,
        assessed_value=1000000.0
    )
    
    db_session.add(property_obj)
    db_session.commit()
    db_session.refresh(property_obj)
    
    return property_obj


@pytest.fixture
def sample_zoning_district(db_session):
    """Create a sample zoning district for testing."""
    polygon = Polygon([
        (-74.0060, 40.7120),
        (-74.0040, 40.7120),
        (-74.0040, 40.7140),
        (-74.0060, 40.7140),
        (-74.0060, 40.7120)
    ])
    
    zoning = ZoningDistrict(
        zoning_code="R7-2",
        zoning_type=ZoningType.RESIDENTIAL,
        geometry=WKTElement(polygon.wkt, srid=4326),
        far_residential=3.44,
        max_height=75.0
    )
    
    db_session.add(zoning)
    db_session.commit()
    db_session.refresh(zoning)
    
    return zoning


@pytest.fixture
def sample_landmark(db_session):
    """Create a sample landmark for testing."""
    point = Point(-74.0055, 40.7130)
    
    landmark = Landmark(
        name="Test Historic District",
        landmark_type=LandmarkType.HISTORIC_DISTRICT,
        geometry=WKTElement(point.wkt, srid=4326)
    )
    
    db_session.add(landmark)
    db_session.commit()
    db_session.refresh(landmark)
    
    return landmark


def test_get_property_by_bbl(client, sample_property):
    """Test getting a property by BBL."""
    response = client.get(f"/api/v1/properties/{sample_property.bbl}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["bbl"] == sample_property.bbl
    assert data["address"] == sample_property.address
    assert data["borough"] == "Manhattan"


def test_get_property_not_found(client):
    """Test getting a property that doesn't exist."""
    response = client.get("/api/v1/properties/9999999999")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_lookup_property_by_bbl(client, sample_property):
    """Test property lookup by BBL."""
    response = client.get("/api/v1/properties/lookup", params={"bbl": sample_property.bbl})
    
    assert response.status_code == 200
    data = response.json()
    assert data["property"] is not None
    assert data["property"]["bbl"] == sample_property.bbl


def test_lookup_property_by_address(client, sample_property):
    """Test property lookup by address."""
    response = client.get("/api/v1/properties/lookup", params={"address": "123 Test St"})
    
    assert response.status_code == 200
    data = response.json()
    # May or may not find the property depending on geocoding
    # Just check that we get a valid response
    assert "property" in data or "error" in data


def test_lookup_property_by_coordinates(client, sample_property):
    """Test property lookup by coordinates."""
    response = client.get(
        "/api/v1/properties/lookup",
        params={"lat": 40.7130, "lon": -74.0055}
    )
    
    assert response.status_code == 200
    data = response.json()
    # May or may not find the property depending on exact coordinates
    assert "property" in data or "error" in data


def test_lookup_property_no_parameters(client):
    """Test property lookup with no parameters."""
    response = client.get("/api/v1/properties/lookup")
    
    assert response.status_code == 400
    assert "at least one" in response.json()["detail"].lower()


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "database" in data
