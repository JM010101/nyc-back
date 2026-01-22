"""
Tests for geocoding service.
"""
import pytest
from app.services.geocoding import GeocodingService, GeocodingError


def test_geocoding_service_initialization():
    """Test geocoding service can be initialized."""
    service = GeocodingService()
    assert service.provider in ["nyc", "google"]


def test_normalize_address():
    """Test address normalization."""
    service = GeocodingService()
    
    # Test basic normalization
    normalized = service.normalize_address("123 Main St")
    assert "New York" in normalized or "NY" in normalized
    
    # Test already normalized address
    normalized2 = service.normalize_address("123 Main St, New York, NY")
    assert normalized2 == "123 Main St, New York, NY"


@pytest.mark.asyncio
async def test_geocode_nyc_address():
    """Test geocoding with NYC geocoding API."""
    service = GeocodingService()
    service.provider = "nyc"
    
    try:
        lat, lon = await service.geocode("350 5th Ave, New York, NY 10118")
        assert isinstance(lat, float)
        assert isinstance(lon, float)
        assert -90 <= lat <= 90
        assert -180 <= lon <= 180
    except GeocodingError:
        # If geocoding fails (network issue, etc.), skip test
        pytest.skip("Geocoding API unavailable")


@pytest.mark.asyncio
async def test_geocode_invalid_address():
    """Test geocoding with invalid address."""
    service = GeocodingService()
    service.provider = "nyc"
    
    with pytest.raises(GeocodingError):
        await service.geocode("This is not a real address 12345")


def test_geocoding_error():
    """Test GeocodingError exception."""
    error = GeocodingError("Test error")
    assert str(error) == "Test error"
