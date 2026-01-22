"""
Zoning district data importer.
Imports NYC zoning district data from Shapefile format.
"""
import geopandas as gpd
from sqlalchemy.orm import Session
from typing import Optional, Dict
from tqdm import tqdm
import logging

from app.models.zoning import ZoningDistrict, ZoningType
from geoalchemy2 import WKTElement

logger = logging.getLogger(__name__)


class ZoningImporter:
    """Importer for zoning district data."""
    
    def __init__(self, db: Session):
        self.db = db
        # Zoning code lookup table for FAR and height
        self.zoning_lookup = self._load_zoning_lookup()
    
    def import_file(
        self,
        file_path: str,
        batch_size: int = 500,
        update_existing: bool = False,
        dry_run: bool = False
    ) -> dict:
        """
        Import zoning district data from a file.
        
        Args:
            file_path: Path to Shapefile
            batch_size: Number of records to process before committing
            update_existing: If True, update existing records; if False, skip duplicates
            dry_run: If True, don't actually insert data
        
        Returns:
            Dictionary with import statistics
        """
        logger.info(f"Loading zoning data from {file_path}")
        
        # Read GeoDataFrame
        gdf = gpd.read_file(file_path)
        
        # Ensure CRS is WGS84 (EPSG:4326)
        if gdf.crs is None:
            logger.warning("No CRS found, assuming WGS84")
            gdf.set_crs("EPSG:4326", inplace=True)
        elif gdf.crs.to_string() != "EPSG:4326":
            logger.info(f"Reprojecting from {gdf.crs} to EPSG:4326")
            gdf = gdf.to_crs("EPSG:4326")
        
        logger.info(f"Loaded {len(gdf)} zoning districts")
        
        stats = {
            "total": len(gdf),
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0
        }
        
        if dry_run:
            logger.info("DRY RUN - No data will be inserted")
            return stats
        
        # Process in batches
        for idx in tqdm(range(0, len(gdf), batch_size), desc="Importing zoning districts"):
            batch = gdf.iloc[idx:idx + batch_size]
            
            for _, row in batch.iterrows():
                try:
                    # Extract zoning code
                    zoning_code = self._extract_zoning_code(row)
                    if not zoning_code:
                        stats["skipped"] += 1
                        continue
                    
                    # Check if zoning district exists
                    existing = self.db.query(ZoningDistrict).filter(
                        ZoningDistrict.zoning_code == zoning_code
                    ).first()
                    
                    if existing and not update_existing:
                        stats["skipped"] += 1
                        continue
                    
                    # Extract zoning data
                    zoning_data = self._extract_zoning_data(row, zoning_code)
                    
                    if existing and update_existing:
                        # Update existing district
                        for key, value in zoning_data.items():
                            setattr(existing, key, value)
                        stats["updated"] += 1
                    else:
                        # Create new district
                        zoning_district = ZoningDistrict(**zoning_data)
                        self.db.add(zoning_district)
                        stats["inserted"] += 1
                
                except Exception as e:
                    logger.error(f"Error processing zoning district: {e}")
                    stats["errors"] += 1
                    continue
            
            # Commit batch
            self.db.commit()
        
        logger.info(f"Import complete: {stats}")
        return stats
    
    def _extract_zoning_code(self, row) -> Optional[str]:
        """Extract zoning code from row data."""
        # Common field names for zoning code
        for field in ["ZONEDIST", "ZONEDIST1", "ZONE", "ZONING", "ZONING_CODE"]:
            if field in row and row[field]:
                return str(row[field]).strip()
        return None
    
    def _extract_zoning_data(self, row, zoning_code: str) -> dict:
        """Extract zoning district data from GeoDataFrame row."""
        # Determine zoning type from code
        zoning_type = self._determine_zoning_type(zoning_code)
        
        # Get FAR and height from lookup table
        lookup_data = self.zoning_lookup.get(zoning_code, {})
        
        # Get geometry
        geometry = row.geometry
        
        return {
            "zoning_code": zoning_code,
            "zoning_type": zoning_type,
            "geometry": WKTElement(geometry.wkt, srid=4326),  # Convert to WKT for PostGIS
            "far_residential": lookup_data.get("far_residential"),
            "far_commercial": lookup_data.get("far_commercial"),
            "max_height": lookup_data.get("max_height"),
            "setback_requirements": lookup_data.get("setback_requirements")
        }
    
    def _determine_zoning_type(self, zoning_code: str) -> ZoningType:
        """Determine zoning type from zoning code."""
        code_upper = zoning_code.upper()
        
        if code_upper.startswith("R"):
            return ZoningType.RESIDENTIAL
        elif code_upper.startswith("C"):
            return ZoningType.COMMERCIAL
        elif code_upper.startswith("M"):
            return ZoningType.MANUFACTURING
        else:
            return ZoningType.MIXED
    
    def _load_zoning_lookup(self) -> Dict[str, dict]:
        """
        Load zoning code lookup table with FAR and height information.
        This is a simplified version - in production, this would be loaded from
        a comprehensive zoning regulations database.
        """
        # Example lookup - in production, this would be a comprehensive database
        return {
            # Residential zones
            "R7-2": {"far_residential": 3.44, "far_commercial": None, "max_height": None},
            "R8": {"far_residential": 6.02, "far_commercial": None, "max_height": None},
            # Commercial zones
            "C6-2": {"far_residential": None, "far_commercial": 10.0, "max_height": None},
            # Manufacturing zones
            "M1-5": {"far_residential": None, "far_commercial": None, "max_height": None},
        }
