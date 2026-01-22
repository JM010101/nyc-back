"""
Create property-zoning relationships by spatially intersecting properties with zoning districts.
This should be run after importing both properties and zoning districts.
"""
import click
import logging
from sqlalchemy.orm import Session
from tqdm import tqdm

from app.database import SessionLocal
from app.models.property import Property
from app.services.spatial import SpatialService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--batch-size", default=100, help="Number of properties to process per batch")
@click.option("--limit", default=None, type=int, help="Limit number of properties to process (for testing)")
def create_relationships(batch_size: int, limit: int):
    """
    Create property-zoning relationships by spatially intersecting properties with zoning districts.
    """
    db = SessionLocal()
    
    try:
        # Get all properties
        query = db.query(Property)
        if limit:
            query = query.limit(limit)
        properties = query.all()
        
        click.echo(f"Processing {len(properties)} properties...")
        
        spatial_service = SpatialService(db)
        created = 0
        skipped = 0
        
        for property_obj in tqdm(properties, desc="Creating relationships"):
            try:
                # Check if relationships already exist
                existing_count = len(spatial_service.get_property_zoning_districts(property_obj))
                
                if existing_count > 0:
                    skipped += 1
                    continue
                
                # Create relationships
                spatial_service.create_property_zoning_relationships(property_obj)
                created += 1
                
                # Commit periodically
                if created % batch_size == 0:
                    db.commit()
            
            except Exception as e:
                logger.error(f"Error processing property {property_obj.bbl}: {e}")
                db.rollback()
                continue
        
        # Final commit
        db.commit()
        
        click.echo("")
        click.echo(f"Relationships created: {created}")
        click.echo(f"Properties skipped (already have relationships): {skipped}")
        click.echo("Done!")
        
    except Exception as e:
        db.rollback()
        click.echo(f"Error: {e}", err=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import logging
    create_relationships()
