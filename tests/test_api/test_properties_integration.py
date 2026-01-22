"""
Integration tests for property API endpoints.
Tests the full flow from API request to database response.
"""
import pytest
from geoalchemy2 import WKTElement
from shapely.geometry import Point, Polygon

from app.models.property import Property, Borough
from app.models.zoning import ZoningDistrict, ZoningType, PropertyZoning
from app.models.landmark import Landmark, LandmarkType


@pytest.fixture
def sample_property_with_zoning(db_session):
    """Create a sample property with zoning district relationship."""
    # Create property
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
    db_session.flush()
    
    # Create zoning district
    zoning_polygon = Polygon([
        (-74.0060, 40.7120),
        (-74.0040, 40.7120),
        (-74.0040, 40.7140),
        (-74.0060, 40.7140),
        (-74.0060, 40.7120)
    ])
    
    zoning = ZoningDistrict(
        zoning_code="R7-2",
        zoning_type=ZoningType.RESIDENTIAL,
        geometry=WKTElement(zoning_polygon.wkt, srid=4326),
        far_residential=3.44,
        max_height=75.0
    )
    db_session.add(zoning)
    db_session.flush()
    
    # Create relationship
    property_zoning = PropertyZoning(
        property_id=property_obj.id,
        zoning_district_id=zoning.id,
        is_primary=True
    )
    db_session.add(property_zoning)
    db_session.commit()
    db_session.refresh(property_obj)
    
    return property_obj


@pytest.fixture
def nearby_landmark(db_session, sample_property_with_zoning):
    """Create a landmark near the property."""
    # Create landmark point close to property
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


def test_property_lookup_with_zoning_and_landmarks(
    client, sample_property_with_zoning, nearby_landmark
):
    """Test complete property lookup with zoning and landmarks."""
    response = client.get(
        f"/api/v1/properties/lookup?bbl={sample_property_with_zoning.bbl}"
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["property"] is not None
    assert data["property"]["bbl"] == sample_property_with_zoning.bbl
    assert len(data["property"]["zoning_districts"]) > 0
    assert data["property"]["zoning_districts"][0]["code"] == "R7-2"
    assert data["property"]["zoning_districts"][0]["is_primary"] is True
    assert len(data["property"]["nearby_landmarks"]) > 0


def test_property_lookup_invalid_bbl(client):
    """Test property lookup with invalid BBL."""
    response = client.get("/api/v1/properties/lookup?bbl=9999999999")
    
    assert response.status_code == 200
    data = response.json()
    assert data["property"] is None
    assert data["error"] == "Property not found"


def test_property_lookup_empty_params(client):
    """Test property lookup with no parameters."""
    response = client.get("/api/v1/properties/lookup")
    
    assert response.status_code == 400
    assert "at least one" in response.json()["detail"].lower()


def test_property_by_bbl_endpoint(client, sample_property_with_zoning):
    """Test direct BBL endpoint."""
    response = client.get(f"/api/v1/properties/{sample_property_with_zoning.bbl}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["bbl"] == sample_property_with_zoning.bbl
    assert data["address"] == sample_property_with_zoning.address


def test_property_by_bbl_not_found(client):
    """Test BBL endpoint with non-existent BBL."""
    response = client.get("/api/v1/properties/9999999999")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_property_lookup_multiple_zoning_districts(client, db_session):
    """Test property with multiple zoning districts."""
    # Create property
    polygon = Polygon([
        (-74.0059, 40.7128),
        (-74.0050, 40.7128),
        (-74.0050, 40.7135),
        (-74.0059, 40.7135),
        (-74.0059, 40.7128)
    ])
    
    property_obj = Property(
        bbl="1000120002",
        address="456 Test St, Manhattan",
        borough=Borough.MANHATTAN,
        block=2,
        lot=2,
        geometry=WKTElement(polygon.wkt, srid=4326),
    )
    db_session.add(property_obj)
    db_session.flush()
    
    # Create multiple zoning districts
    for i, code in enumerate(["R7-2", "C6-2"]):
        zoning_polygon = Polygon([
            (-74.0060 - i * 0.001, 40.7120),
            (-74.0040 - i * 0.001, 40.7120),
            (-74.0040 - i * 0.001, 40.7140),
            (-74.0060 - i * 0.001, 40.7140),
            (-74.0060 - i * 0.001, 40.7120)
        ])
        
        zoning = ZoningDistrict(
            zoning_code=code,
            zoning_type=ZoningType.RESIDENTIAL if i == 0 else ZoningType.COMMERCIAL,
            geometry=WKTElement(zoning_polygon.wkt, srid=4326),
        )
        db_session.add(zoning)
        db_session.flush()
        
        property_zoning = PropertyZoning(
            property_id=property_obj.id,
            zoning_district_id=zoning.id,
            is_primary=(i == 0)
        )
        db_session.add(property_zoning)
    
    db_session.commit()
    
    # Test lookup
    response = client.get(f"/api/v1/properties/lookup?bbl={property_obj.bbl}")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["property"]["zoning_districts"]) == 2
    assert any(zd["is_primary"] for zd in data["property"]["zoning_districts"])
