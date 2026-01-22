"""
PostGIS utility functions for spatial operations.
"""
from geoalchemy2 import Geometry
from geoalchemy2.functions import ST_DWithin, ST_Intersects, ST_Distance, ST_GeomFromText
from sqlalchemy import func
from shapely.geometry import Point
from typing import Tuple


def create_point(latitude: float, longitude: float, srid: int = 4326) -> func:
    """
    Create a PostGIS POINT geometry from lat/lon coordinates.
    
    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        srid: Spatial reference system identifier (default: 4326 for WGS84)
    
    Returns:
        PostGIS geometry function
    """
    return ST_GeomFromText(f'POINT({longitude} {latitude})', srid)


def feet_to_meters(feet: float) -> float:
    """Convert feet to meters for PostGIS geography operations."""
    return feet * 0.3048


def meters_to_feet(meters: float) -> float:
    """Convert meters to feet."""
    return meters / 0.3048


def within_distance(
    geometry_column: Geometry,
    point: func,
    distance_feet: float
) -> func:
    """
    Check if geometry is within distance of a point using PostGIS geography.
    
    Args:
        geometry_column: PostGIS geometry column
        point: PostGIS POINT geometry
        distance_feet: Distance in feet
    
    Returns:
        PostGIS boolean function
    """
    distance_meters = feet_to_meters(distance_feet)
    return ST_DWithin(
        func.cast(geometry_column, func.geography),
        func.cast(point, func.geography),
        distance_meters
    )


def calculate_distance(
    geometry1: Geometry,
    geometry2: Geometry
) -> func:
    """
    Calculate distance between two geometries in meters.
    
    Returns:
        PostGIS distance function (returns meters)
    """
    return ST_Distance(
        func.cast(geometry1, func.geography),
        func.cast(geometry2, func.geography)
    )


def intersects(geometry1: Geometry, geometry2: Geometry) -> func:
    """
    Check if two geometries intersect.
    
    Returns:
        PostGIS boolean function
    """
    return ST_Intersects(geometry1, geometry2)
