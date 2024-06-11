#!/bin/bash

function import_shapefile() {
  echo "Start importing $1 into PostGIS"
  ogr2ogr -select CLC18 -f "PostgreSQL" PG:"host=$HOSTNAME user=$PGUSER dbname=$PGDB password=$PGPASSWORD" -nln public.corine $1
  echo "Done"
}

function append_shapefile() {
  echo "Start appending $1 into PostGIS"
  ogr2ogr -f "PostgreSQL" PG:"host=$HOSTNAME user=$PGUSER dbname=$PGDB password=$PGPASSWORD" -nln public.corine -append -update $1
  echo "Done"
}


# Import environment vars
set -o allexport
source ../.env
set +o allexport

# Change working dir
pushd ../../tmp

# Download from BKG
wget https://daten.gdz.bkg.bund.de/produkte/dlm/clc5_2018/aktuell/clc5_2018.utm32s.shape.zip

# Unzip archive
unzip clc5_2018.utm32s.shape.zip

pushd clc5_2018.utm32s.shape/clc5

import_shapefile clc5_class1xx.shp
append_shapefile clc5_class2xx.shp
append_shapefile clc5_class3xx.shp
append_shapefile clc5_class4xx.shp
append_shapefile clc5_class5xx.shp





