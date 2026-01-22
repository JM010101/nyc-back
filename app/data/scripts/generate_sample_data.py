"""
Generate sample test data for development and testing.
This creates minimal sample data so the system can be tested without downloading large NYC files.
"""
import click
from sqlalchemy.orm import Session
from geoalchemy2 import WKTElement
from shapely.geometry import Point, Polygon
import random
from datetime import date

from app.database import SessionLocal
from app.models.property import Property, Borough
from app.models.zoning import ZoningDistrict, ZoningType
from app.models.landmark import Landmark, LandmarkType
from app.models.zoning import PropertyZoning


def create_sample_property(db: Session, bbl: str, borough: Borough, 
                          address: str, center_lon: float, center_lat: float) -> Property:
    """Create a sample property with a small polygon around given coordinates."""
    # Create a small square polygon (approximately 100x100 feet)
    # Roughly 0.0003 degrees ≈ 100 feet in NYC area
    offset = 0.0003
    
    polygon = Polygon([
        (center_lon - offset, center_lat - offset),
        (center_lon + offset, center_lat - offset),
        (center_lon + offset, center_lat + offset),
        (center_lon - offset, center_lat + offset),
        (center_lon - offset, center_lat - offset)
    ])
    
    property_obj = Property(
        bbl=bbl,
        address=address,
        borough=borough,
        block=int(bbl[1:6]),
        lot=int(bbl[6:10]),
        geometry=WKTElement(polygon.wkt, srid=4326),
        land_area=random.uniform(2000, 10000),
        year_built=random.randint(1900, 2020),
        num_floors=random.randint(1, 10),
        units_res=random.randint(0, 50),
        units_total=random.randint(1, 100),
        assessed_value=random.uniform(500000, 5000000),
        zoning_districts=["R7-2"]
    )
    
    db.add(property_obj)
    return property_obj


def create_sample_zoning_district(db: Session, code: str, center_lon: float, 
                                 center_lat: float) -> ZoningDistrict:
    """Create a sample zoning district."""
    # Create a larger polygon covering the area
    offset = 0.001
    
    polygon = Polygon([
        (center_lon - offset, center_lat - offset),
        (center_lon + offset, center_lat - offset),
        (center_lon + offset, center_lat + offset),
        (center_lon - offset, center_lat + offset),
        (center_lon - offset, center_lat - offset)
    ])
    
    # Determine zoning type from code
    if code.startswith("R"):
        zoning_type = ZoningType.RESIDENTIAL
        far_residential = random.uniform(2.0, 6.0)
        far_commercial = None
    elif code.startswith("C"):
        zoning_type = ZoningType.COMMERCIAL
        far_residential = None
        far_commercial = random.uniform(6.0, 15.0)
    elif code.startswith("M"):
        zoning_type = ZoningType.MANUFACTURING
        far_residential = None
        far_commercial = None
    else:
        zoning_type = ZoningType.MIXED
        far_residential = random.uniform(2.0, 6.0)
        far_commercial = random.uniform(6.0, 12.0)
    
    zoning = ZoningDistrict(
        zoning_code=code,
        zoning_type=zoning_type,
        geometry=WKTElement(polygon.wkt, srid=4326),
        far_residential=far_residential,
        far_commercial=far_commercial,
        max_height=random.uniform(50, 200),
        setback_requirements={"front": 10, "rear": 20}
    )
    
    db.add(zoning)
    return zoning


def create_sample_landmark(db: Session, name: str, landmark_type: LandmarkType,
                          center_lon: float, center_lat: float) -> Landmark:
    """Create a sample landmark."""
    # Create a point or small polygon
    if landmark_type == LandmarkType.INDIVIDUAL:
        geometry = Point(center_lon, center_lat)
    else:
        # For districts, create a small polygon
        offset = 0.0005
        polygon = Polygon([
            (center_lon - offset, center_lat - offset),
            (center_lon + offset, center_lat - offset),
            (center_lon + offset, center_lat + offset),
            (center_lon - offset, center_lat + offset),
            (center_lon - offset, center_lat - offset)
        ])
        geometry = polygon
    
    landmark = Landmark(
        name=name,
        landmark_type=landmark_type,
        geometry=WKTElement(geometry.wkt, srid=4326),
        designation_date=date(1970, 1, 1)
    )
    
    db.add(landmark)
    return landmark


@click.command()
@click.option("--clear-existing", is_flag=True, help="Clear existing data before generating")
def generate_sample_data(clear_existing: bool):
    """Generate sample test data for development and testing."""
    db = SessionLocal()
    
    try:
        if clear_existing:
            click.echo("Clearing existing data...")
            db.query(PropertyZoning).delete()
            db.query(Property).delete()
            db.query(ZoningDistrict).delete()
            db.query(Landmark).delete()
            db.commit()
        
        click.echo("Generating sample data...")
        
        # Manhattan sample area (around Central Park)
        manhattan_lon = -73.9654
        manhattan_lat = 40.7829
        
        # Create sample zoning districts
        click.echo("Creating zoning districts...")
        zoning_r7 = create_sample_zoning_district(db, "R7-2", manhattan_lon, manhattan_lat)
        zoning_c6 = create_sample_zoning_district(db, "C6-2", manhattan_lon + 0.002, manhattan_lat)
        db.commit()
        
        # Create sample properties
        click.echo("Creating properties...")
        prop1 = create_sample_property(
            db, "1000120001", Borough.MANHATTAN,
            "123 Central Park West, Manhattan", manhattan_lon, manhattan_lat
        )
        prop2 = create_sample_property(
            db, "1000120002", Borough.MANHATTAN,
            "125 Central Park West, Manhattan", manhattan_lon + 0.0003, manhattan_lat
        )
        prop3 = create_sample_property(
            db, "1000120003", Borough.MANHATTAN,
            "127 Central Park West, Manhattan", manhattan_lon + 0.0006, manhattan_lat
        )
        db.commit()
        
        # Create property-zoning relationships
        click.echo("Creating property-zoning relationships...")
        pz1 = PropertyZoning(
            property_id=prop1.id,
            zoning_district_id=zoning_r7.id,
            is_primary=True
        )
        pz2 = PropertyZoning(
            property_id=prop2.id,
            zoning_district_id=zoning_r7.id,
            is_primary=True
        )
        pz3 = PropertyZoning(
            property_id=prop3.id,
            zoning_district_id=zoning_c6.id,
            is_primary=True
        )
        db.add_all([pz1, pz2, pz3])
        db.commit()
        
        # Create sample landmarks
        click.echo("Creating landmarks...")
        # Landmark close to properties (within 150 feet)
        landmark1 = create_sample_landmark(
            db, "Central Park Historic District", LandmarkType.HISTORIC_DISTRICT,
            manhattan_lon + 0.0002, manhattan_lat + 0.0002
        )
        # Individual landmark
        landmark2 = create_sample_landmark(
            db, "Sample Individual Landmark", LandmarkType.INDIVIDUAL,
            manhattan_lon + 0.0001, manhattan_lat
        )
        db.commit()
        
        click.echo("")
        click.echo("Sample data generated successfully!")
        click.echo("")
        click.echo("Sample properties:")
        click.echo(f"  - BBL: 1000120001 (123 Central Park West)")
        click.echo(f"  - BBL: 1000120002 (125 Central Park West)")
        click.echo(f"  - BBL: 1000120003 (127 Central Park West)")
        click.echo("")
        click.echo("You can now test the API:")
        click.echo("  curl http://localhost:8000/health")
        click.echo("  curl 'http://localhost:8000/api/v1/properties/lookup?bbl=1000120001'")
        click.echo("  curl 'http://localhost:8000/api/v1/properties/1000120001'")
        
    except Exception as e:
        db.rollback()
        click.echo(f"Error generating sample data: {e}", err=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    generate_sample_data()
