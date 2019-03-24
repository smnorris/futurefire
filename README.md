# futurefire

 Generate annual burned forest areas as rasters of random ellipses. Buffer roads and overlay with burn raster to create potential salvage areas.


# Requirements

Python >=3.5 (tested with 3.7.2)


# Installation

With conda:

    git clone https://github.com/smnorris/futurefire
    cd futurefire
    conda env create
    conda activate futurefire
    pip install .

With pip:

    git clone https://github.com/smnorris/futurefire
    cd futurefire
    pip install .

If installing via pip on Windows, you will need to first download and install the appropriate [pre-compiled gdal and rasterio Python wheels](https://www.lfd.uci.edu/~gohlke/pythonlibs/) for your version of Python. Conda handles this for you.


# Data prep

The script handles most data prep but to quickly ensure no edge areas are lost, the BC regions raster was manually prepared from the NRCAN provided regions polygons:

  - edit polygons to extend beyond BC Border / into ocean (ensuring regions cover all areas)
  - reproject to `EPSG:3005`
  - assign integers to regions : `{1: Coast, 2: Northern Interior, 3: Southern Interior}`
  - rasterize, aligning to provided 1ha Hectares BC `inputs\isbc.tif`
  - extract only cells on land in BC (where `isbc.tif=1`)
  - output is provided as `inputs\regions.tif`


# Usage

Load input inventory and road data to raster, buffer road raster:

    futurefire load


Create all burns for a given `scenario.csv` file (with required columns `burnid`, `year`, `region`, `runid`, `area`) using default configuration settings:

    futurefire burn scenario.csv

To override the default configuration, use the `--config_file` option to provide `futurefire` with the path to your config file:

    futurefire load --config_file path/to/myconfig.cfg
    futurefire burn scenario.csv --config_file path/to/myconfig.cfg

[`sample_config.cfg`](sample_config.cfg) illustrates the parameters that can be configured.

The `burn` command includes additional options for running just a specific region / run / year. There is also an option for using a forest image other the default raster created by `futurefire load` (default is derived from the `inventory` layer specified in the config):

    $ futurefire burn --help
    Usage: futurefire burn [OPTIONS] SCENARIO_CSV

      Read scenario csv and apply fires to the landscape

    Options:
      -c, --config_file PATH  Path to configuration file
      --runid TEXT            Process only burns with this runid
      --region TEXT           Process only burns in this region
      --year TEXT             Process only burns for this year
      --forest_image PATH     Path to alternative forest image
      --help                  Show this message and exit.


# Method

## load
- rasterize inventory, creating 1ha grid in area preserving projection with raster extent/alignment matching a Hectares BC sample raster
- rasterize roads, creating 1ha grid in area preserving projection
- buffer the roads by distance specifiied in config (default 500m)

## burn

For each region / run / year, iterate through fires in the scenario csv:
  - randomly place fire centres within forested area
  - create randomly oriented ellipse at fire centre with target area noted in scenario csv
  - determine how much forest is within the ellipse
  - expand the ellipse until forest area within ellipse meets or exceeds the target burn area (default expansion is 5% area)
  - choose the ellipse with the burned forest area closest to the target burn area (from the final two expansions)
  - record the burn in the output burn image
  - record that the burn has occured in the forest image

Once all fires have been placed for the given region / run / year:
  - set burned areas in the forest image back to forest if the regen interval has taken place
  - export burn geotiff

Finally, generate / export a salvage geotiff (areas of burn that overlap the buffered roads image) to the `output` folder defined in config


# Development and testing

    git clone https://github.com/smnorris/futurefire
    cd futurefire
    conda env create
    conda activate futurefire
    conda install pytest
    pip install -e .