from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from app.database import get_db
from app.services.spatial import SpatialService
from app.services.geocoding import GeocodingService, GeocodingError
from app.schemas.property import PropertyResponse, PropertyLookupQuery
from app.schemas.response import PropertyLookupResponse
from app.utils.postgis import create_point

router = APIRouter()


@router.get("/lookup", response_model=PropertyLookupResponse)
async def lookup_property(
    address: Optional[str] = Query(None, description="Property address"),
    bbl: Optional[str] = Query(None, description="BBL (Borough-Block-Lot)"),
    lat: Optional[float] = Query(None, ge=-90, le=90, description="Latitude"),
    lon: Optional[float] = Query(None, ge=-180, le=180, description="Longitude"),
    db: Session = Depends(get_db)
):
    """
    Look up a property by address, BBL, or coordinates.
    
    Returns property information including:
    - Basic property details (address, BBL, borough, etc.)
    - Zoning districts
    - Nearby landmarks (within 150 feet)
    """
    # Validate that at least one parameter is provided
    if not any([address, bbl, (lat is not None and lon is not None)]):
        raise HTTPException(
            status_code=400,
            detail="At least one of address, bbl, or lat/lon must be provided"
        )
    
    spatial_service = SpatialService(db)
    property_obj = None
    
    try:
        # Try BBL lookup first (most direct)
        if bbl:
            property_obj = spatial_service.find_property_by_bbl(bbl)
        
        # Try address lookup
        elif address:
            # First try direct address match
            property_obj = spatial_service.find_property_by_address(address)
            
            # If not found, geocode and search by coordinates
            if not property_obj:
                geocoding_service = GeocodingService()
                normalized_address = geocoding_service.normalize_address(address)
                lat, lon = await geocoding_service.geocode(normalized_address)
                property_obj = spatial_service.find_property_by_coordinates(lat, lon)
        
        # Try coordinate lookup
        elif lat is not None and lon is not None:
            property_obj = spatial_service.find_property_by_coordinates(lat, lon)
        
        if not property_obj:
            return PropertyLookupResponse(
                property=None,
                error="Property not found"
            )
        
        # Get zoning districts
        zoning_districts = spatial_service.get_property_zoning_districts(property_obj)
        if not zoning_districts:
            # Fallback to spatial intersection if no relationships exist
            zoning_districts = spatial_service.get_zoning_districts(property_obj.geometry)
        
        # Get nearby landmarks
        nearby_landmarks = spatial_service.find_nearby_landmarks(
            property_obj.geometry,
            distance_feet=150.0
        )
        
        # Build response
        from app.schemas.property import ZoningDistrictInfo, NearbyLandmarkInfo
        
        zoning_info = [
            ZoningDistrictInfo(
                code=zd.zoning_code,
                type=zd.zoning_type.value,
                is_primary=is_primary
            )
            for zd, is_primary in zoning_districts
        ]
        
        landmark_info = [
            NearbyLandmarkInfo(
                name=lm.name,
                landmark_type=lm.landmark_type.value,
                distance_feet=round(distance_ft, 2)
            )
            for lm, distance_ft in nearby_landmarks
        ]
        
        property_response = PropertyResponse(
            id=property_obj.id,
            bbl=property_obj.bbl,
            address=property_obj.address,
            borough=property_obj.borough.value,
            block=property_obj.block,
            lot=property_obj.lot,
            land_area=float(property_obj.land_area) if property_obj.land_area else None,
            year_built=property_obj.year_built,
            num_floors=property_obj.num_floors,
            units_res=property_obj.units_res,
            units_total=property_obj.units_total,
            assessed_value=float(property_obj.assessed_value) if property_obj.assessed_value else None,
            zoning_districts=zoning_info,
            nearby_landmarks=landmark_info,
            created_at=property_obj.created_at,
            updated_at=property_obj.updated_at
        )
        
        return PropertyLookupResponse(property=property_response)
    
    except GeocodingError as e:
        raise HTTPException(status_code=400, detail=f"Geocoding error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{bbl}", response_model=PropertyResponse)
def get_property_by_bbl(
    bbl: str,
    db: Session = Depends(get_db)
):
    """
    Get a property by BBL (Borough-Block-Lot).
    
    Returns detailed property information.
    """
    spatial_service = SpatialService(db)
    property_obj = spatial_service.find_property_by_bbl(bbl)
    
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Get zoning districts
    zoning_districts = spatial_service.get_property_zoning_districts(property_obj)
    if not zoning_districts:
        zoning_districts = spatial_service.get_zoning_districts(property_obj.geometry)
    
    # Get nearby landmarks
    nearby_landmarks = spatial_service.find_nearby_landmarks(
        property_obj.geometry,
        distance_feet=150.0
    )
    
    # Build response
    from app.schemas.property import ZoningDistrictInfo, NearbyLandmarkInfo
    
    zoning_info = [
        ZoningDistrictInfo(
            code=zd.zoning_code,
            type=zd.zoning_type.value,
            is_primary=is_primary
        )
        for zd, is_primary in zoning_districts
    ]
    
    landmark_info = [
        NearbyLandmarkInfo(
            name=lm.name,
            landmark_type=lm.landmark_type.value,
            distance_feet=round(distance_ft, 2)
        )
        for lm, distance_ft in nearby_landmarks
    ]
    
    return PropertyResponse(
        id=property_obj.id,
        bbl=property_obj.bbl,
        address=property_obj.address,
        borough=property_obj.borough.value,
        block=property_obj.block,
        lot=property_obj.lot,
        land_area=float(property_obj.land_area) if property_obj.land_area else None,
        year_built=property_obj.year_built,
        num_floors=property_obj.num_floors,
        units_res=property_obj.units_res,
        units_total=property_obj.units_total,
        assessed_value=float(property_obj.assessed_value) if property_obj.assessed_value else None,
        zoning_districts=zoning_info,
        nearby_landmarks=landmark_info,
        created_at=property_obj.created_at,
        updated_at=property_obj.updated_at
    )
