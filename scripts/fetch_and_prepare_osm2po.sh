#!/bin/bash

pushd ../../tmp

mkdir osm2po

pushd osm2po

# Download
wget https://osm2po.de/releases/osm2po-5.5.5.zip

# Unzip archive
unzip osm2po-5.5.5.zip

rm osm2po-5.5.5.zip