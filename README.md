# futurefire

Randomly generate burned areas for future fire scenarios

# Usage

    futurefire createdb
    futurefire load
    futurefire compute

# Requirements

    Installation is easiest when managing the Python environment with Anaconda / conda.


# Installation

    git clone https://github.com/smnorris/futurefire
    cd futurefire
    conda env create
    conda activate futurefire
    pip install .


# Method

- rasterize inventory

for each event:
  - randomly place start (within forested area)
  - choose an axis for expansion (from 8 directions)
  - expand 1.5x up 1x down within forested area to required area
  - stepwise expansion  n cells, with probability of expansion in each direction determined randomly
  - assign result to non-forest for x years


# prep data

- BC regions was manually prepared to ensure no edge areas were lost:
    - edit polygons to extend beyond BC Border / into ocean, delete islands
    - reproject to EPSG:3005
    - rasterize using 1ha grid
    - extract only cells where isbc==1

- because gdal does not reproject on rasterize, reproject roads and inventory to an area preserving projection (BC Albers). Write to .gpkg to avoid fussing with the File Geodatabase API

    ogr2ogr -progress -f GPKG -t_srs EPSG:3005 inputs_alb.gpkg future_fire_2019_01_24.gdb roads

    ogr2ogr -progress -update -f GPKG -t_srs EPSG:3005 inputs_alb.gpkg future_fire_2019_01_24.gdb inventory


- rasterize inventory:

    gdal_rasterize -burn 1 -l inventory -te 159587.5 173787.5 1881187.5 1748187.5 -tr 100 100 -tap -co COMPRESS=DEFLATE inputs_alb.gdb roads.tif

- rasterize roads and apply buffer using 1ha cells:

    gdal_rasterize -burn 1 -l roads -dialect SQLITE -sql "SELECT * FROM roads WHERE RD_SURFACE != 'ferry'" -te 159587.5 173787.5 1881187.5 1748187.5 -tr 100 100 -tap -co COMPRESS=DEFLATE inputs_alb.gdb roads.tif

    gdal_proximity.py -ot byte -co COMPRESS=DEFLATE -distunits GEO -maxdist 500 -fixed-buf-val 1 roads.tif roads_dist.tif

- If we wanted to experiment with buffer distances, one option would be to  rasterize roads @ 10m then generate a high resolution proximity grid with values corresponding to distance to road. A 1ha cell would probably be fine too.

    gdal_rasterize -burn 1 -l roads -te 159587.5 173787.5 1881187.5 1748187.5 -tr 10 10 -tap -co COMPRESS=DEFLATE -co inputs_alb.gdb roads_10m.tif

    gdal_proximity.py -ot Int16 -co COMPRESS=DEFLATE -co BIGTIFF=YES -distunits GEO -maxdist 1000 roads_10m.tif roads_dist_10m.tif

# Development and testing

    git clone https://github.com/smnorris/futurefire
    cd futurefire
    conda env create
    conda activate futurefire
    conda install pytest
    pip install -e .