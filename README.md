# futurefire

Randomly generate burned areas for future fire scenarios

# Usage

    futurefire createdb
    futurefire load
    futurefire compute

# Requirements

- Python 3 (tested with v3.7)
- GDAL/OGR (tested with v2.4.0)
- PostgreSQL (tested with v11.2)
- PostGIS (tested with v2.5.1)

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

