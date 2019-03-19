# futurefire

Generate random burned forest areas for future fire scenarios.


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

If installing via pip on Windows, you will likely have to first download install [pre-compiled gdal and rasterio Python wheels](https://www.lfd.uci.edu/~gohlke/pythonlibs/). Conda handles this for you.


# Data prep

The script handles most data prep but to quickly ensure no edge areas were lost, the BC regions raster was manually prepared:

  - edit polygons to extend beyond BC Border / into ocean (ensuring regions cover all areas)
  - reproject to `EPSG:3005`
  - assign integers to regions : `{1: Coast, 2: Northern Interior, 3: Southern Interior}`
  - rasterize, aligning to provided 1ha Hectares BC `data\isbc.tif`
  - extract only cells on land in BC (where `isbc.tif=1`)
  - output is provided as `data\regions.tif`

# Usage

Load data to raster:

    futurefire load


Create all burns for a given `scenario.csv` file using default configuration settings:

    futurefire burn scenario.csv


To override the default configuration, use the `--config_file` option to provide `futurefire` with the path to your config file:

    futurefire load --config_file path/to/myconfig.cfg
    futurefire burn scenario.csv --config_file path/to/myconfig.cfg

[`sample_config.cfg`](sammple_config.cfg) shows the parameters that can be configured.


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
  - randomly place fire centre within forested area
  - create a randomly oriented ellipse at fire centre with target area noted in scenario csv
  - determine how much forest is within the ellipse
  - expand the ellipse by 1% until forest area within ellipse meets or exceeds the target burn area
  - choose the ellipse with the burned forest area closest to the target burn area
  - note the burn in the output burn image
  - note that the burn has occured in the forest image
  - set burned areas in the forest image back to forest if the regen interval has taken place

## dump

Export all burn geotiffs and generate / export salvage tiffs (areas of burn that overlap the buffered roads image) to the folder defined in config `output`


# Development and testing

    git clone https://github.com/smnorris/futurefire
    cd futurefire
    conda env create
    conda activate futurefire
    conda install pytest
    pip install -e .