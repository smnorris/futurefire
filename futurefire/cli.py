import os
import logging
from subprocess import Popen, PIPE
import subprocess

import click
import pandas
import rasterio

import futurefire
from futurefire import util
from futurefire.config import config


util.configure_logging()
log = logging.getLogger(__name__)


@click.group()
def cli():
    pass


@cli.command()
@click.option("--config_file", "-c", help="Configuration file")
@click.option("--wksp", "-w", help="Override config workspace")
def load(config_file, wksp):
    """
    Load roads and inventory to area-preserving rasters, then buffer roads
    """
    # NOTE
    # Just to keep things basic we use gdal utilities directly rather than
    # gdal.rasterize() or fiona/rasterio.
    # To ensure cross-platform compatibility, call the commands here with
    # subprocess rather than via a bash/shell script.
    if config_file:
        util.load_config(config_file)
    # used for testing
    if wksp:
        config["wksp"] = wksp

    util.make_sure_path_exists(config["wksp"])

    # reproject to area preserving coordinate reference system
    cmd1 = ["ogr2ogr",
        "-f",
        "GPKG",
        "-t_srs",
        "EPSG:3005",
        os.path.join(config["wksp"], "roads.gpkg"),
        config["inputs_gdb"],
        config["roads"]
    ]
    cmd2 = ["ogr2ogr",
        "-f",
        "GPKG",
        "-t_srs",
        "EPSG:3005",
        os.path.join(config["wksp"], "inventory.gpkg"),
        config["inputs_gdb"],
        config["inventory"]
    ]
    cmds = [cmd1, cmd2]
    for cmd in cmds:
        log.info(" ".join(cmd))
    procs_list = [Popen(cmd) for cmd in cmds]
    for proc in procs_list:
        proc.wait()

    # now rasterize
    cmd1 = [
        "gdal_rasterize",
        "-burn",
        "1",
        "-l",
        "inventory",
        "-te",
        config["bounds"][0],
        config["bounds"][1],
        config["bounds"][2],
        config["bounds"][3],
        "-tr",
        str(config["cell_size"]),
        str(config["cell_size"]),
        "-tap",
        "-co",
        "COMPRESS=DEFLATE",
        "-q",
        os.path.join(config["wksp"], "inventory.gpkg"),
        os.path.join(config["wksp"], "inventory.tif")
    ]

    cmd2 = [
        "gdal_rasterize",
        "-burn",
        "1",
        "-l",
        "roads",
        "-dialect",
        "SQLITE",
        "-sql",
        "SELECT * FROM roads WHERE RD_SURFACE != 'boat'",
        "-te",
        config["bounds"][0],
        config["bounds"][1],
        config["bounds"][2],
        config["bounds"][3],
        "-tr",
        str(config["cell_size"]),
        str(config["cell_size"]),
        "-tap",
        "-co",
        "COMPRESS=DEFLATE",
        "-q",
        os.path.join(config["wksp"], "roads.gpkg"),
        os.path.join(config["wksp"], "roads.tif")
    ]
    cmds = [cmd1, cmd2]
    for cmd in cmds:
        log.info(" ".join(cmd))
    procs_list = [Popen(cmd) for cmd in cmds]
    for proc in procs_list:
        proc.wait()

    # finally, buffer the roads
    cmd = ["gdal_proximity.py",
        "-ot",
        "byte",
        "-co",
        "COMPRESS=DEFLATE",
        "-distunits",
        "GEO",
        "-maxdist",
        str(config["buffer"]),
        "-fixed-buf-val",
        "1",
        os.path.join(config["wksp"], "roads.tif"),
        os.path.join(config["wksp"], "roads_buf.tif")
    ]
    log.info(" ".join(cmd))
    subprocess.run(cmd)


@cli.command()
@click.option("--config_file", "-c", help="Configuration file")
def burn(config_file, scenario_csv, forest_image, runid, region, year):
    """Read input csv and apply fires to the landscape
    """
    # load scenario csv and find unique run/region/year values
    fires_df = pandas.read_csv(scenario_csv)
    runids = list(fires_df.runid.unique())
    regions = list(fires_df.region.unique())
    years = list(fires_df.year.unique())

    # filter fire records to work with based on options
    if runid:
        if runid in runids:
            fires = fires_df["runid"] == runid
        else:
            raise ValueError("runid {} not present in {}".format(str(runid), scenario_csv))
    if region:
        if region in regions:
            fires = fires_df["region"] == region
        else:
            raise ValueError("region {} not present in {}".format(region, scenario_csv))
    if year:
        if year in years:
            fires = fires_df["year"] == year
        else:
            raise ValueError("year {} not present in {}".format(year, scenario_csv))

    # load source forested image
    with rasterio.open(forest_image) as src:
        forest = src.read()

    # create output csv for logging individual fire stats
    # (how many iterations to create, actual burnt forest area)
    with open(config["out_csv"], 'w', newline='') as csvfile:
        fieldnames = ["burnid", "iteration", "burned_forest_area"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

    # iterate through the region/run/years
    for region in regions:
        fires =  fires[fires['region'] == region]

        # restrict processing to given region
        region_forest = forest[region_image == config[region_lookup]]

        for runid in runids:
            fires = fires['runid'] == run

            # initialize forest tracking raster for the run
            forest_current = region_forest.copy()

            for year in years:
                fires = fires['year'] == year
                # initialize output burned year raster
                burned = np.zeros(shape=forest.shape)
                # create burn ellipses
                futurefire.apply_fires(fires, forest_image, burn_image, year)
                # export current year to tiff
                futurefire.export_fires(burned, run, year, region)
                # set current forest to 1 where it has been regen years since
                # pixel burned
                forest_current[burned == (year - config["regen"])] = 1

if __name__ == '__main__':
    cli()