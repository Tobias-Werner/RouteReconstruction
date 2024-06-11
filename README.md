# Route Reconstruction

## Requirements
* podman
* podman-compose


## Prepare

Install Python dependencies
```
pip3 install -r requirements.txt
```

Building pgrouting-enabled postgis image
```
podman-compose build
```

Create ```.env``` file using ```.env.template```

## Run Database
Running postgis

```
podman-compose up
```

## Import Basic Data
Do import of several data by scripts in `/scripts`

* `fetch_and_import_corine_2018.sh` imports CORINE dataset to classify routes into region types.
* `fetch_and_import_germany_boundaries.sh` imports boundaries of Germany to spatially filter routes.  
* `fetch_and_import_laea_cells.sh` imports laea grid to perform heatmap anaylsis.
* `fetch_and_prepare_osm2po.sh` downloads and prepare osm2po to create a network topology.
* `fetch_and_import_osm_network.sh` imports OpenStreetMap network as topology for routing.

## Synchronize Car Data

Calling `route_reconstruction/lib/enviro_car.py` with 

* `createschema` to create the database schema
* `syncdb` to fetch and synchronize upstream car data


## Processing

Performing processing and analysis from `/route_reconstruction/processing`

* `do_1_reset_processing_schema.py` resets database processing schema
* `do_2_track_analysis.py` transforms und reprojects measurements to linestring geometries (EPSG:28532)
* `do_3_exclude_tracks.py` performs filter steps to exclude error-related and not-processable tracks
* `do_4_interpolate_speeds.py` interpolates speed measurements to second-by-second data 
* `do_5_intersect_corine.py` intersects tracks with CORINE to optain region type proportions per track
* `do_6_track_similarity.py` calculates Hausdorff and Frechet distances on all tracks
* `do_7_reconstruct_p2p.py` performs shortest and fastest route calculation
* `do_8_analysis.py` analysis shortest and fastest route results by region types

## Generate Plots

Plots can be created by calling scripts in `/route_reconstruction/plot`

* `tracks_map_overview.py` generates an overview map of tracks within germany
* `tracks_map_overview_density.py` generates a heatmap of tracks within germany
* `track_group_speed_comparison.py` generates a speed comparison of a group of similar tracks
* `track_p2p_shortest_fastest.py` generates a comparison of a fastest, shortest and custom track   
* `tracks_p2p_multi_step_filter.py` shows network reduction by intersection and Dijkstra filter
* `track_p2p_speed_comparison.py` illustrates phenomena matching along linear referenced distance
* `tracks_proportions_overview.py` generates a classification of tracks into region types
* `tracks_duplicates.py` illustrates similarity by Hausdorff and Frechet in a group of tracks





















