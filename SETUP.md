# Backend Setup Guide

## Initial Setup Steps

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your database URL
   ```

3. **Create database and enable PostGIS**
   ```sql
   CREATE DATABASE nyc_zoning;
   \c nyc_zoning
   CREATE EXTENSION IF NOT EXISTS postgis;
   ```

4. **Create initial migration**
   ```bash
   alembic revision --autogenerate -m "Initial migration"
   ```

5. **Apply migrations**
   ```bash
   alembic upgrade head
   ```

6. **Generate sample data** (for testing)
   ```bash
   # Generate sample test data (no downloads required)
   python -m app.data.scripts.generate_sample_data
   
   # Or import real NYC data (requires downloading files first)
   # See scripts/setup_sample_data.sh or setup_sample_data.ps1
   python -m app.data.scripts.import_data mappluto --file /path/to/mappluto.geojson
   ```

7. **Run the server**
   ```bash
   uvicorn app.main:app --reload
   ```

## Common Issues

### PostGIS Extension Not Found
If you get an error about PostGIS extension:
- Make sure PostgreSQL is installed with PostGIS support
- For Docker: Use `postgis/postgis:15-3.4` image
- For local install: Install `postgresql-postgis` package

### Geometry Import Errors
If geometry import fails:
- Ensure GeoPandas is installed: `pip install geopandas`
- Check that shapefiles are valid and have proper CRS
- Verify PostGIS extension is enabled in database

### Database Connection Errors
- Check DATABASE_URL in .env file
- Ensure PostgreSQL is running
- Verify database exists and user has proper permissions
