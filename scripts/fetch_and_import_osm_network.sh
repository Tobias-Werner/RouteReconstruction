#!/bin/bash

cp -f osm2po.config ../../tmp/osm2po/

pushd ../../tmp

wget https://download.geofabrik.de/europe/germany-latest.osm.pbf

export JAVACMD_OPTIONS=-Xmx12G
export JAVACMD_OPTIONS=-server

pushd osm2po

java -Xmx4g -jar osm2po-core-5.5.5-signed.jar prefix=de tileSize=x cmd=tjsp workDir=../osm2po_result ../germany-latest.osm.pbf postp.0.class=de.cm.osm2po.plugins.postp.PgRoutingWriter

popd
popd

set -o allexport
source ../.env
set +o allexport

psql -h $HOSTNAME -U $PGUSER -d $PGDB -q -f "../../tmp/osm2po_result/de_2po_4pgr.sql"

