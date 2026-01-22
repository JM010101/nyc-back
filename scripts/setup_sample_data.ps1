# PowerShell script to set up sample data for testing
# This script assumes you have downloaded NYC Open Data files

Write-Host "NYC Real Estate Zoning Platform - Sample Data Setup" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Check if data directory exists
if (-not (Test-Path "..\data\raw")) {
    Write-Host "Creating data/raw directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path "..\data\raw" -Force | Out-Null
}

Write-Host "Please download the following NYC Open Data files to data/raw/:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. MapPLUTO (Property parcels):"
Write-Host "   https://data.cityofnewyork.us/City-Government/MapPLUTO/2qhw-4x8y"
Write-Host "   Save as: data/raw/mappluto.geojson"
Write-Host ""
Write-Host "2. Zoning Districts:"
Write-Host "   https://data.cityofnewyork.us/City-Government/Zoning-Districts/..."
Write-Host "   Save as: data/raw/zoning.shp (and associated files)"
Write-Host ""
Write-Host "3. Landmarks:"
Write-Host "   https://data.cityofnewyork.us/Housing-Development/Landmarks/..."
Write-Host "   Save as: data/raw/landmarks.shp (and associated files)"
Write-Host ""
Read-Host "Press Enter once you have downloaded the files"

# Check if files exist
$mapplutoFile = $null
if (Test-Path "..\data\raw\mappluto.geojson") {
    $mapplutoFile = "..\data\raw\mappluto.geojson"
} elseif (Test-Path "..\data\raw\mappluto.shp") {
    $mapplutoFile = "..\data\raw\mappluto.shp"
}

if (-not $mapplutoFile) {
    Write-Host "ERROR: MapPLUTO file not found in data/raw/" -ForegroundColor Red
    exit 1
}

# Import data
Write-Host ""
Write-Host "Importing MapPLUTO data..." -ForegroundColor Green
python -m app.data.scripts.import_data mappluto --file $mapplutoFile --batch-size 1000

Write-Host ""
Write-Host "Importing zoning districts..." -ForegroundColor Green
if (Test-Path "..\data\raw\zoning.shp") {
    python -m app.data.scripts.import_data zoning --file ..\data\raw\zoning.shp --batch-size 500
} else {
    Write-Host "WARNING: Zoning districts file not found, skipping..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Importing landmarks..." -ForegroundColor Green
if (Test-Path "..\data\raw\landmarks.shp") {
    python -m app.data.scripts.import_data landmarks --file ..\data\raw\landmarks.shp --batch-size 500
} else {
    Write-Host "WARNING: Landmarks file not found, skipping..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Sample data import complete!" -ForegroundColor Green
Write-Host ""
Write-Host "You can now test the API:" -ForegroundColor Cyan
Write-Host "  curl http://localhost:8000/health"
Write-Host "  curl 'http://localhost:8000/api/v1/properties/lookup?bbl=1000120001'"
