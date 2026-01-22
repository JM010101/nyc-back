"""
Spatial query service for PostGIS operations.
Handles spatial queries like finding nearby landmarks, intersecting zoning districts, etc.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from geoalchemy2 import Geometry
from geoalchemy2.functions import ST_DWithin, ST_Intersects, ST_Distance, ST_GeomFromText
from typing import List, Optional, Tuple
from shapely.geometry import Point

from app.models.property import Property
from app.models.zoning import ZoningDistrict, PropertyZoning
from app.models.landmark import Landmark
from app.utils.postgis import create_point, within_distance, calculate_distance, intersects


class SpatialService:
    """Service for spatial queries using PostGIS."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def find_property_by_bbl(self, bbl: str) -> Optional[Property]:
        """
        Find a property by BBL (Borough-Block-Lot).
        
        Args:
            bbl: BBL string (e.g., "1000120001")
        
        Returns:
            Property object or None if not found
        """
        return self.db.query(Property).filter(Property.bbl == bbl).first()
    
    def find_property_by_address(self, address: str) -> Optional[Property]:
        """
        Find a property by address (exact match).
        
        Args:
            address: Property address
        
        Returns:
            Property object or None if not found
        """
        return self.db.query(Property).filter(Property.address.ilike(f"%{address}%")).first()
    
    def find_property_by_coordinates(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[Property]:
        """
        Find a property by coordinates using spatial intersection.
        
        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
        
        Returns:
            Property object that contains the point, or None if not found
        """
        point = create_point(latitude, longitude)
        
        # Find property that contains the point
        property = self.db.query(Property).filter(
            func.ST_Contains(Property.geometry, point)
        ).first()
        
        return property
    
    def find_nearby_landmarks(
        self,
        geometry: Geometry,
        distance_feet: float = 150.0
    ) -> List[Tuple[Landmark, float]]:
        """
        Find landmarks within a specified distance of a geometry.
        
        Args:
            geometry: PostGIS geometry (point or polygon)
            distance_feet: Distance in feet (default: 150)
        
        Returns:
            List of tuples (Landmark, distance_in_feet)
        """
        # Convert geometry to geography for accurate distance calculations
        geom_geog = func.cast(geometry, func.geography)
        landmark_geog = func.cast(Landmark.geometry, func.geography)
        
        # Calculate distance in meters, then convert to feet
        distance_meters = func.ST_Distance(geom_geog, landmark_geog)
        
        # Find landmarks within distance
        landmarks = self.db.query(
            Landmark,
            distance_meters.label('distance_meters')
        ).filter(
            ST_DWithin(
                landmark_geog,
                geom_geog,
                distance_feet * 0.3048  # Convert feet to meters
            )
        ).all()
        
        # Convert to list of tuples with distance in feet
        result = []
        for landmark, distance_m in landmarks:
            distance_ft = distance_m / 0.3048
            result.append((landmark, distance_ft))
        
        return result
    
    def get_zoning_districts(
        self,
        geometry: Geometry
    ) -> List[Tuple[ZoningDistrict, bool]]:
        """
        Get all zoning districts that intersect with a geometry.
        
        Args:
            geometry: PostGIS geometry (point or polygon)
        
        Returns:
            List of tuples (ZoningDistrict, is_primary)
        """
        # Find intersecting zoning districts
        districts = self.db.query(ZoningDistrict).filter(
            ST_Intersects(ZoningDistrict.geometry, geometry)
        ).all()
        
        # Check which ones are primary for the property (if applicable)
        result = []
        for district in districts:
            # Try to find if this is a primary zoning for any property
            # For now, we'll mark the first one as primary
            # In a real implementation, you'd check PropertyZoning table
            is_primary = False
            result.append((district, is_primary))
        
        return result
    
    def get_property_zoning_districts(
        self,
        property: Property
    ) -> List[Tuple[ZoningDistrict, bool]]:
        """
        Get zoning districts for a property from the PropertyZoning junction table.
        
        Args:
            property: Property object
        
        Returns:
            List of tuples (ZoningDistrict, is_primary)
        """
        property_zoning = self.db.query(PropertyZoning).filter(
            PropertyZoning.property_id == property.id
        ).all()
        
        result = []
        for pz in property_zoning:
            result.append((pz.zoning_district, pz.is_primary))
        
        return result
    
    def find_adjacent_properties(
        self,
        geometry: Geometry,
        limit: int = 10
    ) -> List[Property]:
        """
        Find properties adjacent to a geometry.
        
        Args:
            geometry: PostGIS geometry
            limit: Maximum number of results
        
        Returns:
            List of adjacent Property objects
        """
        # Find properties that touch or are very close to the geometry
        # Using ST_Touches for exact adjacency or ST_DWithin for near-adjacency
        properties = self.db.query(Property).filter(
            func.ST_Touches(Property.geometry, geometry)
        ).limit(limit).all()
        
        # If no exact touches, try very close (within 1 foot)
        if not properties:
            properties = self.db.query(Property).filter(
                ST_DWithin(
                    func.cast(Property.geometry, func.geography),
                    func.cast(geometry, func.geography),
                    0.3048  # 1 foot in meters
                )
            ).limit(limit).all()
        
        return properties
    
    def create_property_zoning_relationships(
        self,
        property: Property
    ) -> None:
        """
        Create PropertyZoning relationships by spatially intersecting
        property geometry with zoning district geometries.
        
        Args:
            property: Property object
        """
        # Find intersecting zoning districts
        districts = self.db.query(ZoningDistrict).filter(
            ST_Intersects(ZoningDistrict.geometry, property.geometry)
        ).all()
        
        if not districts:
            return
        
        # Create relationships
        # First district is marked as primary
        for i, district in enumerate(districts):
            # Check if relationship already exists
            existing = self.db.query(PropertyZoning).filter(
                PropertyZoning.property_id == property.id,
                PropertyZoning.zoning_district_id == district.id
            ).first()
            
            if not existing:
                property_zoning = PropertyZoning(
                    property_id=property.id,
                    zoning_district_id=district.id,
                    is_primary=(i == 0)  # First one is primary
                )
                self.db.add(property_zoning)
        
        self.db.commit()
