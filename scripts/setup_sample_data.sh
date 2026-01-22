#!/bin/bash
# Helper script to set up sample data for testing
# This script assumes you have downloaded NYC Open Data files

set -e

echo "NYC Real Estate Zoning Platform - Sample Data Setup"
echo "=================================================="
echo ""

# Check if data directory exists
if [ ! -d "../data/raw" ]; then
    echo "Creating data/raw directory..."
    mkdir -p ../data/raw
fi

echo "Please download the following NYC Open Data files to data/raw/:"
echo ""
echo "1. MapPLUTO (Property parcels):"
echo "   https://data.cityofnewyork.us/City-Government/MapPLUTO/2qhw-4x8y"
echo "   Save as: data/raw/mappluto.geojson"
echo ""
echo "2. Zoning Districts:"
echo "   https://data.cityofnewyork.us/City-Government/Zoning-Districts/..."
echo "   Save as: data/raw/zoning.shp (and associated files)"
echo ""
echo "3. Landmarks:"
echo "   https://data.cityofnewyork.us/Housing-Development/Landmarks/..."
echo "   Save as: data/raw/landmarks.shp (and associated files)"
echo ""
read -p "Press Enter once you have downloaded the files..."

# Check if files exist
if [ ! -f "../data/raw/mappluto.geojson" ] && [ ! -f "../data/raw/mappluto.shp" ]; then
    echo "ERROR: MapPLUTO file not found in data/raw/"
    exit 1
fi

# Import data
echo ""
echo "Importing MapPLUTO data..."
if [ -f "../data/raw/mappluto.geojson" ]; then
    python -m app.data.scripts.import_data mappluto --file ../data/raw/mappluto.geojson --batch-size 1000
else
    python -m app.data.scripts.import_data mappluto --file ../data/raw/mappluto.shp --batch-size 1000
fi

echo ""
echo "Importing zoning districts..."
if [ -f "../data/raw/zoning.shp" ]; then
    python -m app.data.scripts.import_data zoning --file ../data/raw/zoning.shp --batch-size 500
else
    echo "WARNING: Zoning districts file not found, skipping..."
fi

echo ""
echo "Importing landmarks..."
if [ -f "../data/raw/landmarks.shp" ]; then
    python -m app.data.scripts.import_data landmarks --file ../data/raw/landmarks.shp --batch-size 500
else
    echo "WARNING: Landmarks file not found, skipping..."
fi

echo ""
echo "Sample data import complete!"
echo ""
echo "You can now test the API:"
echo "  curl http://localhost:8000/health"
echo "  curl 'http://localhost:8000/api/v1/properties/lookup?bbl=1000120001'"
