"""
API endpoint for retrieving property geometry data for map visualization.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import Optional

from app.database import get_db
from app.models.property import Property
from app.models.zoning import ZoningDistrict
from app.models.landmark import Landmark

router = APIRouter()


@router.get("/properties/{bbl}/geometry")
def get_property_geometry(
    bbl: str,
    db: Session = Depends(get_db)
):
    """
    Get property geometry as GeoJSON for map visualization.
    
    Returns:
    - Property geometry as GeoJSON
    - Center coordinates (centroid)
    - Bounding box
    """
    property_obj = db.query(Property).filter(Property.bbl == bbl).first()
    
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")
    
    try:
        # Get geometry as GeoJSON
        geom_result = db.execute(
            text("SELECT ST_AsGeoJSON(geometry) as geom FROM properties WHERE bbl = :bbl"),
            {"bbl": bbl}
        ).fetchone()
        
        # Get centroid coordinates
        centroid_result = db.execute(
            text("SELECT ST_X(ST_Centroid(geometry)) as lon, ST_Y(ST_Centroid(geometry)) as lat FROM properties WHERE bbl = :bbl"),
            {"bbl": bbl}
        ).fetchone()
        
        # Get bounding box
        bbox_result = db.execute(
            text("SELECT ST_AsGeoJSON(ST_Envelope(geometry)) as bbox FROM properties WHERE bbl = :bbl"),
            {"bbl": bbl}
        ).fetchone()
        
        return {
            "bbl": bbl,
            "geometry": geom_result.geom if geom_result else None,
            "center": {
                "lon": float(centroid_result.lon) if centroid_result else None,
                "lat": float(centroid_result.lat) if centroid_result else None,
            },
            "bbox": bbox_result.bbox if bbox_result else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving geometry: {str(e)}")


@router.get("/properties/{bbl}/nearby-geometry")
def get_nearby_geometry(
    bbl: str,
    distance_feet: float = 150.0,
    db: Session = Depends(get_db)
):
    """
    Get geometry for property and nearby landmarks/zoning districts.
    
    Returns:
    - Property geometry
    - Nearby landmark geometries
    - Intersecting zoning district geometries
    """
    property_obj = db.query(Property).filter(Property.bbl == bbl).first()
    
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")
    
    try:
        # Get property geometry
        prop_geom = db.execute(
            text("SELECT ST_AsGeoJSON(geometry) as geom FROM properties WHERE bbl = :bbl"),
            {"bbl": bbl}
        ).fetchone()
        
        # Get nearby landmarks
        landmarks = db.execute(
            text("""
                SELECT 
                    id,
                    name,
                    ST_AsGeoJSON(geometry) as geom,
                    ST_Distance(
                        ST_Transform(geometry::geography, 3857),
                        (SELECT ST_Transform(geometry::geography, 3857) FROM properties WHERE bbl = :bbl)
                    ) * 3.28084 as distance_feet
                FROM landmarks
                WHERE ST_DWithin(
                    geometry::geography,
                    (SELECT geometry::geography FROM properties WHERE bbl = :bbl),
                    :distance_meters
                )
                ORDER BY distance_feet
            """),
            {"bbl": bbl, "distance_meters": distance_feet * 0.3048}
        ).fetchall()
        
        # Get intersecting zoning districts
        zoning = db.execute(
            text("""
                SELECT 
                    zd.id,
                    zd.zoning_code,
                    ST_AsGeoJSON(zd.geometry) as geom
                FROM zoning_districts zd
                WHERE ST_Intersects(
                    zd.geometry,
                    (SELECT geometry FROM properties WHERE bbl = :bbl)
                )
            """),
            {"bbl": bbl}
        ).fetchall()
        
        return {
            "property": {
                "bbl": bbl,
                "geometry": prop_geom.geom if prop_geom else None,
            },
            "landmarks": [
                {
                    "id": str(lm.id),
                    "name": lm.name,
                    "geometry": lm.geom,
                    "distance_feet": round(float(lm.distance_feet), 2),
                }
                for lm in landmarks
            ],
            "zoning_districts": [
                {
                    "id": str(zd.id),
                    "zoning_code": zd.zoning_code,
                    "geometry": zd.geom,
                }
                for zd in zoning
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving geometry: {str(e)}")
