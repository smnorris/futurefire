import os
import logging
from subprocess import Popen, PIPE
import subprocess
import csv

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
@click.option("--config_file", "-c", type=click.Path(exists=True), help="Configuration file")
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
@click.argument("scenario_csv", type=click.Path(exists=True))
@click.option("--config_file", "-c", type=click.Path(exists=True), help="Path to configuration file")
@click.option("--runid", help="Process only burns with this runid", type=int)
@click.option("--region", help="Process only burns in this region")
@click.option("--year", help="Process only burns for this year", type=int)
@click.option("--forest_image", type=click.Path(exists=True), help="Path to alternative forest image", default=os.path.join(config["wksp"], "inventory.tif"))
@click.option("-n", help="Number of fires to process per year (for testing)", type=int)
def burn(scenario_csv, config_file, runid, region, year, forest_image, n):
    """Read scenario csv and apply fires to the landscape
    """
    if config_file:
        util.load_config(config_file)
    # load scenario csv and find unique run/region/year values
    fires_df = pandas.read_csv(scenario_csv)

    runids = sorted(list(fires_df.runid.unique()))
    regions = sorted(list(fires_df.region.unique()))
    years = sorted(list(fires_df.year.unique()))

    # filter fire records to work with based on options
    if runid:
        if runid in runids:
            fires_df = fires_df[fires_df["runid"] == runid]
        else:
            raise ValueError("runid {} not present in {}".format(str(runid), scenario_csv))
    if region:
        if region in regions:
            fires_df = fires_df[fires_df["region"] == region]
        else:
            raise ValueError("region {} not present in {}".format(region, scenario_csv))
    if year:
        if year in years:
            fires_df = fires_df[fires_df["year"] == year]
        else:
            raise ValueError("year {} not present in {}".format(year, scenario_csv))

    # load source forested image
    with rasterio.open(forest_image) as src:
        forest = src.read(1)

    # create output csv for logging individual fire stats
    # (how many iterations to create, actual burnt forest area)
    # file is in outputs folder, name is scenario_burn.csv
    scenario = os.path.splitext(os.path.basename(scenario_csv))[0]
    out_path = os.path.join(config["outputs"], scenario)
    util.make_sure_path_exists(out_path)
    burn_csv = os.path.join(out_path, scenario+"_burns.csv")
    with open(burn_csv, 'w', newline='') as csvfile:
        fieldnames = ["burnid", "iteration", "burned_forest_area"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

    # iterate through the region/run/years
    for region in regions:
        fires_df =  fires_df[fires_df['region'] == region]

        # open regions file
        with rasterio.open(config["regions"]) as src:
            regions = src.read(1)

        # set forest for other regions to zero so they don't get processed
        forest[regions != config["region_lookup"][region]] = 0

        for runid in runids:
            fires_df = fires_df['runid'] == runid

            # initialize forest tracking raster for the run
            forest_current = region_forest.copy()

            for year in years:
                fires_df = fires_df['year'] == year
                # initialize output burned year raster
                burn_image = np.zeros(shape=forest.shape)

                # create burns
                forest_current, burn_image, burn_list = futurefire.apply_fires(fires_df, forest_current, burn_image, year, n=n)

                # write burns to disk
                futurefire.write_fires(runid, region, year, burn_image, burn_list, out_path, burn_csv)

                # set forest=1 where it has been regen years since burned
                forest_current[burned == (year - config["regen"])] = 1


if __name__ == '__main__':
    cli()
