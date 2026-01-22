"""
MapPLUTO data importer.
Imports NYC MapPLUTO property data from GeoJSON or Shapefile format.
"""
import geopandas as gpd
from sqlalchemy.orm import Session
from typing import Optional
from tqdm import tqdm
import logging

from app.models.property import Property, Borough
from geoalchemy2 import WKTElement

logger = logging.getLogger(__name__)


class MapPLUTOImporter:
    """Importer for MapPLUTO property data."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def import_file(
        self,
        file_path: str,
        batch_size: int = 1000,
        update_existing: bool = False,
        dry_run: bool = False
    ) -> dict:
        """
        Import MapPLUTO data from a file.
        
        Args:
            file_path: Path to GeoJSON or Shapefile
            batch_size: Number of records to process before committing
            update_existing: If True, update existing records; if False, skip duplicates
            dry_run: If True, don't actually insert data
        
        Returns:
            Dictionary with import statistics
        """
        logger.info(f"Loading MapPLUTO data from {file_path}")
        
        # Read GeoDataFrame
        gdf = gpd.read_file(file_path)
        
        # Ensure CRS is WGS84 (EPSG:4326)
        if gdf.crs is None:
            logger.warning("No CRS found, assuming WGS84")
            gdf.set_crs("EPSG:4326", inplace=True)
        elif gdf.crs.to_string() != "EPSG:4326":
            logger.info(f"Reprojecting from {gdf.crs} to EPSG:4326")
            gdf = gdf.to_crs("EPSG:4326")
        
        logger.info(f"Loaded {len(gdf)} properties")
        
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
        for idx in tqdm(range(0, len(gdf), batch_size), desc="Importing properties"):
            batch = gdf.iloc[idx:idx + batch_size]
            
            for _, row in batch.iterrows():
                try:
                    # Extract BBL
                    bbl = self._extract_bbl(row)
                    if not bbl:
                        stats["skipped"] += 1
                        continue
                    
                    # Check if property exists
                    existing = self.db.query(Property).filter(Property.bbl == bbl).first()
                    
                    if existing and not update_existing:
                        stats["skipped"] += 1
                        continue
                    
                    # Extract property data
                    property_data = self._extract_property_data(row)
                    
                    if existing and update_existing:
                        # Update existing property
                        for key, value in property_data.items():
                            setattr(existing, key, value)
                        stats["updated"] += 1
                    else:
                        # Create new property
                        property_obj = Property(**property_data)
                        self.db.add(property_obj)
                        stats["inserted"] += 1
                
                except Exception as e:
                    logger.error(f"Error processing property: {e}")
                    stats["errors"] += 1
                    continue
            
            # Commit batch
            self.db.commit()
        
        logger.info(f"Import complete: {stats}")
        return stats
    
    def _extract_bbl(self, row) -> Optional[str]:
        """Extract BBL from row data."""
        # MapPLUTO typically has BBL field
        if "BBL" in row:
            bbl = str(row["BBL"])
        elif "bbl" in row:
            bbl = str(row["bbl"])
        else:
            # Try to construct from borough, block, lot
            borough_code = self._get_borough_code(row)
            block = row.get("Block", row.get("block"))
            lot = row.get("Lot", row.get("lot"))
            
            if borough_code and block is not None and lot is not None:
                bbl = f"{borough_code}{int(block):05d}{int(lot):04d}"
            else:
                return None
        
        return bbl.zfill(10)  # Ensure 10 digits
    
    def _get_borough_code(self, row) -> Optional[str]:
        """Get borough code (1=Manhattan, 2=Bronx, 3=Brooklyn, 4=Queens, 5=Staten Island)."""
        borough = row.get("Borough", row.get("borough", row.get("BOROCODE")))
        
        if borough is None:
            return None
        
        borough_str = str(borough).upper()
        borough_map = {
            "1": "1", "MANHATTAN": "1", "MN": "1",
            "2": "2", "BRONX": "2", "BX": "2",
            "3": "3", "BROOKLYN": "3", "BK": "3", "KINGS": "3",
            "4": "4", "QUEENS": "4", "QN": "4",
            "5": "5", "STATEN ISLAND": "5", "SI": "5", "RICHMOND": "5"
        }
        
        return borough_map.get(borough_str)
    
    def _extract_property_data(self, row) -> dict:
        """Extract property data from GeoDataFrame row."""
        bbl = self._extract_bbl(row)
        borough_code = self._get_borough_code(row)
        
        # Map borough code to enum
        borough_map = {
            "1": Borough.MANHATTAN,
            "2": Borough.BRONX,
            "3": Borough.BROOKLYN,
            "4": Borough.QUEENS,
            "5": Borough.STATEN_ISLAND
        }
        
        borough = borough_map.get(borough_code, Borough.MANHATTAN)
        
        # Extract address
        address = row.get("Address", row.get("address"))
        if not address:
            # Try to construct from components
            house_num = row.get("HouseNum", row.get("house_num", ""))
            street = row.get("Street", row.get("street", ""))
            if house_num and street:
                address = f"{house_num} {street}"
        
        # Extract numeric fields
        block = int(row.get("Block", row.get("block", 0)))
        lot = int(row.get("Lot", row.get("lot", 0)))
        land_area = self._safe_float(row.get("LotArea", row.get("lot_area")))
        year_built = self._safe_int(row.get("YearBuilt", row.get("year_built")))
        num_floors = self._safe_int(row.get("NumFloors", row.get("num_floors")))
        units_res = self._safe_int(row.get("UnitsRes", row.get("units_res")))
        units_total = self._safe_int(row.get("UnitsTotal", row.get("units_total")))
        assessed_value = self._safe_float(row.get("AssessTot", row.get("assess_tot")))
        
        # Extract zoning codes
        zoning_districts = []
        if "ZoneDist1" in row and row["ZoneDist1"]:
            zoning_districts.append(str(row["ZoneDist1"]))
        if "ZoneDist2" in row and row["ZoneDist2"]:
            zoning_districts.append(str(row["ZoneDist2"]))
        if "ZoneDist3" in row and row["ZoneDist3"]:
            zoning_districts.append(str(row["ZoneDist3"]))
        if "ZoneDist4" in row and row["ZoneDist4"]:
            zoning_districts.append(str(row["ZoneDist4"]))
        
        # Get geometry (should be a Shapely geometry)
        geometry = row.geometry
        
        return {
            "bbl": bbl,
            "address": address,
            "borough": borough,
            "block": block,
            "lot": lot,
            "geometry": WKTElement(geometry.wkt, srid=4326),  # Convert to WKT for PostGIS
            "land_area": land_area,
            "year_built": year_built,
            "num_floors": num_floors,
            "units_res": units_res,
            "units_total": units_total,
            "assessed_value": assessed_value,
            "zoning_districts": zoning_districts if zoning_districts else None
        }
    
    def _safe_int(self, value) -> Optional[int]:
        """Safely convert value to int."""
        if value is None or value == "":
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
    
    def _safe_float(self, value) -> Optional[float]:
        """Safely convert value to float."""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
