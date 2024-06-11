#!/bin/bash

function import_shapefile() {
  echo "Start importing $1 into PostGIS"
  ogr2ogr -f "PostgreSQL" -explodecollections PG:"host=$HOSTNAME user=$PGUSER dbname=$PGDB password=$PGPASSWORD" -nln public.germany $1
  echo "Done"
}


# Import environment vars
set -o allexport
source ../.env
set +o allexport

# Change working dir
pushd ../../tmp

# Download from BKG
wget https://daten.gdz.bkg.bund.de/produkte/vg/vg5000_1231/aktuell/vg5000_12-31.utm32s.shape.ebenen.zip

# Unzip archive
unzip vg5000_12-31.utm32s.shape.ebenen.zip

pushd vg5000_12-31.utm32s.shape.ebenen/vg5000_ebenen_1231

import_shapefile VG5000_STA.shp





