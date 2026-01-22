"""
CLI script for importing NYC data (MapPLUTO, zoning districts, landmarks).
"""
import click
import logging
from pathlib import Path
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.data.importers.mappluto import MapPLUTOImporter
from app.data.importers.zoning import ZoningImporter
from app.data.importers.landmarks import LandmarkImporter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """NYC Real Estate Data Import Tool."""
    pass


@cli.command()
@click.option("--file", "-f", required=True, type=click.Path(exists=True), help="Path to MapPLUTO file (GeoJSON or Shapefile)")
@click.option("--batch-size", default=1000, help="Batch size for processing")
@click.option("--update-existing", is_flag=True, help="Update existing records instead of skipping")
@click.option("--dry-run", is_flag=True, help="Dry run - don't actually insert data")
def mappluto(file: str, batch_size: int, update_existing: bool, dry_run: bool):
    """Import MapPLUTO property data."""
    db = SessionLocal()
    try:
        importer = MapPLUTOImporter(db)
        stats = importer.import_file(
            file_path=file,
            batch_size=batch_size,
            update_existing=update_existing,
            dry_run=dry_run
        )
        click.echo(f"Import complete: {stats}")
    finally:
        db.close()


@cli.command()
@click.option("--file", "-f", required=True, type=click.Path(exists=True), help="Path to zoning districts Shapefile")
@click.option("--batch-size", default=500, help="Batch size for processing")
@click.option("--update-existing", is_flag=True, help="Update existing records instead of skipping")
@click.option("--dry-run", is_flag=True, help="Dry run - don't actually insert data")
def zoning(file: str, batch_size: int, update_existing: bool, dry_run: bool):
    """Import zoning district data."""
    db = SessionLocal()
    try:
        importer = ZoningImporter(db)
        stats = importer.import_file(
            file_path=file,
            batch_size=batch_size,
            update_existing=update_existing,
            dry_run=dry_run
        )
        click.echo(f"Import complete: {stats}")
    finally:
        db.close()


@cli.command()
@click.option("--file", "-f", required=True, type=click.Path(exists=True), help="Path to landmarks Shapefile")
@click.option("--batch-size", default=500, help="Batch size for processing")
@click.option("--update-existing", is_flag=True, help="Update existing records instead of skipping")
@click.option("--dry-run", is_flag=True, help="Dry run - don't actually insert data")
def landmarks(file: str, batch_size: int, update_existing: bool, dry_run: bool):
    """Import landmark data."""
    db = SessionLocal()
    try:
        importer = LandmarkImporter(db)
        stats = importer.import_file(
            file_path=file,
            batch_size=batch_size,
            update_existing=update_existing,
            dry_run=dry_run
        )
        click.echo(f"Import complete: {stats}")
    finally:
        db.close()


if __name__ == "__main__":
    cli()
