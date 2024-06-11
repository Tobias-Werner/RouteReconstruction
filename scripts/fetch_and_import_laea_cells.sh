#!/bin/bash

function import_shapefile() {
  echo "Start importing $1 into PostGIS"
  ogr2ogr -s_srs EPSG:3035 -t_srs EPSG:25832 -f "PostgreSQL" PG:"host=$HOSTNAME user=$PGUSER dbname=$PGDB password=$PGPASSWORD" -nln $2 $1
  echo "Done"
}


# Import environment vars
set -o allexport
source ../.env
set +o allexport

# Change working dir
pushd ../../tmp

# Download from BKG
#wget https://daten.gdz.bkg.bund.de/produkte/sonstige/geogitter/aktuell/DE_Grid_ETRS89-LAEA_500m.gpkg.zip
wget https://daten.gdz.bkg.bund.de/produkte/sonstige/geogitter/aktuell/DE_Grid_ETRS89-LAEA_5km.gpkg.zip

# Unzip archive
#unzip DE_Grid_ETRS89-LAEA_500m.gpkg.zip
unzip DE_Grid_ETRS89-LAEA_5km.gpkg.zip

#pushd DE_Grid_ETRS89-LAEA_500m.gpkg/geogitter
#import_shapefile DE_Grid_ETRS89-LAEA_500m.gpkg public.laea_500m

pushd DE_Grid_ETRS89-LAEA_5km.gpkg/geogitter
import_shapefile DE_Grid_ETRS89-LAEA_5km.gpkg public.laea_5km





