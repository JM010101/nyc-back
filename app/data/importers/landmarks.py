"""
Landmark data importer.
Imports NYC landmark data from Shapefile format.
"""
import geopandas as gpd
from sqlalchemy.orm import Session
from typing import Optional
from tqdm import tqdm
import logging
from datetime import datetime

from app.models.landmark import Landmark, LandmarkType
from geoalchemy2 import WKTElement

logger = logging.getLogger(__name__)


class LandmarkImporter:
    """Importer for landmark data."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def import_file(
        self,
        file_path: str,
        batch_size: int = 500,
        update_existing: bool = False,
        dry_run: bool = False
    ) -> dict:
        """
        Import landmark data from a file.
        
        Args:
            file_path: Path to Shapefile
            batch_size: Number of records to process before committing
            update_existing: If True, update existing records; if False, skip duplicates
            dry_run: If True, don't actually insert data
        
        Returns:
            Dictionary with import statistics
        """
        logger.info(f"Loading landmark data from {file_path}")
        
        # Read GeoDataFrame
        gdf = gpd.read_file(file_path)
        
        # Ensure CRS is WGS84 (EPSG:4326)
        if gdf.crs is None:
            logger.warning("No CRS found, assuming WGS84")
            gdf.set_crs("EPSG:4326", inplace=True)
        elif gdf.crs.to_string() != "EPSG:4326":
            logger.info(f"Reprojecting from {gdf.crs} to EPSG:4326")
            gdf = gdf.to_crs("EPSG:4326")
        
        logger.info(f"Loaded {len(gdf)} landmarks")
        
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
        for idx in tqdm(range(0, len(gdf), batch_size), desc="Importing landmarks"):
            batch = gdf.iloc[idx:idx + batch_size]
            
            for _, row in batch.iterrows():
                try:
                    # Extract landmark name
                    name = self._extract_name(row)
                    if not name:
                        stats["skipped"] += 1
                        continue
                    
                    # Check if landmark exists (by name - could be improved with unique ID)
                    existing = self.db.query(Landmark).filter(
                        Landmark.name == name
                    ).first()
                    
                    if existing and not update_existing:
                        stats["skipped"] += 1
                        continue
                    
                    # Extract landmark data
                    landmark_data = self._extract_landmark_data(row, name)
                    
                    if existing and update_existing:
                        # Update existing landmark
                        for key, value in landmark_data.items():
                            setattr(existing, key, value)
                        stats["updated"] += 1
                    else:
                        # Create new landmark
                        landmark = Landmark(**landmark_data)
                        self.db.add(landmark)
                        stats["inserted"] += 1
                
                except Exception as e:
                    logger.error(f"Error processing landmark: {e}")
                    stats["errors"] += 1
                    continue
            
            # Commit batch
            self.db.commit()
        
        logger.info(f"Import complete: {stats}")
        return stats
    
    def _extract_name(self, row) -> Optional[str]:
        """Extract landmark name from row data."""
        # Common field names for landmark name
        for field in ["NAME", "LM_NAME", "LANDMARK_NAME", "DESIG_NAME"]:
            if field in row and row[field]:
                return str(row[field]).strip()
        return None
    
    def _extract_landmark_data(self, row, name: str) -> dict:
        """Extract landmark data from GeoDataFrame row."""
        # Determine landmark type
        landmark_type = self._determine_landmark_type(row)
        
        # Extract designation date
        designation_date = self._extract_designation_date(row)
        
        # Get geometry
        geometry = row.geometry
        
        return {
            "name": name,
            "landmark_type": landmark_type,
            "geometry": WKTElement(geometry.wkt, srid=4326),  # Convert to WKT for PostGIS
            "designation_date": designation_date
        }
    
    def _determine_landmark_type(self, row) -> LandmarkType:
        """Determine landmark type from row data."""
        # Check for type field
        type_field = row.get("TYPE", row.get("LM_TYPE", row.get("LANDMARK_TYPE", "")))
        type_str = str(type_field).upper()
        
        if "DISTRICT" in type_str or "HISTORIC DISTRICT" in type_str:
            return LandmarkType.HISTORIC_DISTRICT
        elif "SCENIC" in type_str:
            return LandmarkType.SCENIC
        else:
            return LandmarkType.INDIVIDUAL
    
    def _extract_designation_date(self, row) -> Optional[datetime]:
        """Extract designation date from row data."""
        # Common field names for designation date
        for field in ["DESIG_DATE", "DESIGNATION_DATE", "DATE_DESIG"]:
            if field in row and row[field]:
                try:
                    date_str = str(row[field])
                    # Try various date formats
                    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y%m%d"]:
                        try:
                            return datetime.strptime(date_str, fmt).date()
                        except ValueError:
                            continue
                except Exception:
                    continue
        return None
