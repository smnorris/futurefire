import os
import logging
from subprocess import Popen
import subprocess
import csv

import click
import pandas as pd
import numpy as np
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
@click.option(
    "--config_file", "-c", type=click.Path(exists=True), help="Configuration file"
)
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
    cmd1 = [
        "ogr2ogr",
        "-f",
        "GPKG",
        "-t_srs",
        "EPSG:3005",
        os.path.join(config["wksp"], "roads.gpkg"),
        config["inputs_gdb"],
        config["roads"],
    ]
    cmd2 = [
        "ogr2ogr",
        "-f",
        "GPKG",
        "-t_srs",
        "EPSG:3005",
        os.path.join(config["wksp"], "inventory.gpkg"),
        config["inputs_gdb"],
        config["inventory"],
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
        "-co",
        "COMPRESS=DEFLATE",
        "-q",
        os.path.join(config["wksp"], "inventory.gpkg"),
        os.path.join(config["wksp"], "inventory.tif"),
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
        "-co",
        "COMPRESS=DEFLATE",
        "-q",
        os.path.join(config["wksp"], "roads.gpkg"),
        os.path.join(config["wksp"], "roads.tif"),
    ]
    cmds = [cmd1, cmd2]
    for cmd in cmds:
        log.info(" ".join(cmd))
    procs_list = [Popen(cmd) for cmd in cmds]
    for proc in procs_list:
        proc.wait()

    # finally, buffer the roads
    cmd = [
        "gdal_proximity.py",
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
        os.path.join(config["wksp"], "roads_buf.tif"),
    ]
    log.info(" ".join(cmd))
    subprocess.run(cmd)


@cli.command()
@click.argument("scenario_csv", type=click.Path(exists=True))
@click.option(
    "--config_file",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration file",
)
@click.option("--runid", help="Process only burns with this runid", type=int)
@click.option("--region", help="Process only burns in this region")
@click.option("--year", help="Process only burns for this year", type=int)
@click.option(
    "--forest_tif",
    type=click.Path(exists=True),
    help="Override config path to forest image",
)
@click.option("-n", help="Number of fires to process per year (for testing)", type=int)
def burn(scenario_csv, config_file, runid, region, year, forest_tif, n):
    """Read scenario csv and apply fires to the landscape
    """
    if config_file:
        util.load_config(config_file)
    if not forest_tif:
        forest_tif = os.path.join(config["wksp"], "inventory.tif")

    # load scenario csv and find unique run/region/year values
    fires_df = pd.read_csv(scenario_csv)

    runids = sorted(list(fires_df.runid.unique()))
    regions = sorted(list(fires_df.region.unique()))
    years = sorted(list(fires_df.year.unique()))

    # filter fire records to work with based on options
    if runid:
        if runid in runids:
            fires_df = fires_df[fires_df["runid"] == runid]
        else:
            raise ValueError(
                "runid {} not present in {}".format(str(runid), scenario_csv)
            )
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

    # reload the distinct values after filtered by options
    if runid or region or year:
        runids = sorted(list(fires_df.runid.unique()))
        regions = sorted(list(fires_df.region.unique()))
        years = sorted(list(fires_df.year.unique()))

    # create output csv for logging individual fire stats
    # (how many iterations to create, actual burnt forest area)
    # file is in outputs folder, name is scenario_burn.csv
    scenario = os.path.splitext(os.path.basename(scenario_csv))[0]
    out_path = os.path.join(config["outputs"], scenario)
    util.make_sure_path_exists(out_path)
    burn_csv = os.path.join(out_path, scenario + "_burns.csv")
    with open(burn_csv, "w", newline="") as csvfile:
        fieldnames = [
            "burnid",
            "year",
            "region",
            "runid",
            "target_area",
            "iteration",
            "burned_forest_area",
            "ellipse_area",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

    # open regions file
    with rasterio.open(config["regions"]) as src:
        regions_image = src.read(1)

    # loop through burns in order of run / region / year
    for runid in runids:
        log.info("Processing runid {}".format(runid))

        # load forest raster
        with rasterio.open(forest_tif) as src:
            forest_prov = src.read(1)

        for year in years:

            # initialize output burned year raster and list
            burn_image = np.zeros(shape=forest_prov.shape)
            burn_list = []

            for region in regions:

                # get fires for given region/runid/year combo
                fires = fires_df[
                    (fires_df["region"] == region)
                    & (fires_df["runid"] == runid)
                    & (fires_df["year"] == year)
                ]
                # initialize forest for region of interest
                forest_reg = forest_prov.copy()
                forest_reg[regions_image != config["region_lookup"][region]] = 0

                # create burns
                burn_list = burn_list + futurefire.apply_fires(
                    fires, forest_reg, forest_prov, burn_image, runid, region, year, n=n
                )

            # write burns to disk
            futurefire.write_fires(
                runid, year, burn_image, burn_list, out_path, burn_csv
            )
            # set forest=1 where it has been regen years since burned
            # (& correct region)
            forest_prov[(burn_image == (year - config["regen"])) & (regions == config["region_lookup"][region])] = 1


if __name__ == "__main__":
    cli()
