"""
Geocoding service for converting addresses to coordinates.
Supports NYC Geocoding API and Google Maps Geocoding API.
"""
import httpx
from typing import Optional, Tuple
from app.config import settings


class GeocodingError(Exception):
    """Custom exception for geocoding errors."""
    pass


class GeocodingService:
    """Service for geocoding addresses to coordinates."""
    
    def __init__(self):
        self.provider = settings.GEOCODING_PROVIDER.lower()
        self.api_key = settings.GEOCODING_API_KEY
    
    async def geocode(self, address: str) -> Tuple[float, float]:
        """
        Geocode an address to latitude and longitude.
        
        Args:
            address: Address string (e.g., "123 Main St, New York, NY")
        
        Returns:
            Tuple of (latitude, longitude)
        
        Raises:
            GeocodingError: If geocoding fails
        """
        if self.provider == "nyc":
            return await self._geocode_nyc(address)
        elif self.provider == "google":
            return await self._geocode_google(address)
        else:
            raise GeocodingError(f"Unknown geocoding provider: {self.provider}")
    
    async def _geocode_nyc(self, address: str) -> Tuple[float, float]:
        """
        Geocode using NYC Geocoding API (free, no API key required).
        
        API Documentation: https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html
        """
        base_url = "https://geocoding.geo.census.gov/geocoder/locations/address"
        
        params = {
            "street": address,
            "city": "New York",
            "state": "NY",
            "benchmark": "Public_AR_Current",
            "format": "json"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if not data.get("result", {}).get("addressMatches"):
                    raise GeocodingError(f"No results found for address: {address}")
                
                match = data["result"]["addressMatches"][0]
                coordinates = match["coordinates"]
                
                return (
                    float(coordinates["y"]),  # latitude
                    float(coordinates["x"])   # longitude
                )
            except httpx.HTTPError as e:
                raise GeocodingError(f"HTTP error during geocoding: {str(e)}")
            except (KeyError, ValueError, IndexError) as e:
                raise GeocodingError(f"Error parsing geocoding response: {str(e)}")
    
    async def _geocode_google(self, address: str) -> Tuple[float, float]:
        """
        Geocode using Google Maps Geocoding API.
        Requires GEOCODING_API_KEY to be set.
        """
        if not self.api_key:
            raise GeocodingError("Google Maps API key not configured")
        
        base_url = "https://maps.googleapis.com/maps/api/geocode/json"
        
        params = {
            "address": address,
            "key": self.api_key
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data.get("status") != "OK":
                    error_msg = data.get("error_message", "Unknown error")
                    raise GeocodingError(f"Google Geocoding API error: {error_msg}")
                
                if not data.get("results"):
                    raise GeocodingError(f"No results found for address: {address}")
                
                location = data["results"][0]["geometry"]["location"]
                
                return (
                    float(location["lat"]),
                    float(location["lng"])
                )
            except httpx.HTTPError as e:
                raise GeocodingError(f"HTTP error during geocoding: {str(e)}")
            except (KeyError, ValueError, IndexError) as e:
                raise GeocodingError(f"Error parsing geocoding response: {str(e)}")
    
    def normalize_address(self, address: str) -> str:
        """
        Normalize address string for better geocoding results.
        
        Args:
            address: Raw address string
        
        Returns:
            Normalized address string
        """
        # Remove extra whitespace
        address = " ".join(address.split())
        
        # Ensure NYC is included if not present
        if "new york" not in address.lower() and "ny" not in address.lower():
            address = f"{address}, New York, NY"
        
        return address


# Singleton instance
geocoding_service = GeocodingService()
