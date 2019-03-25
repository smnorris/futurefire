import os
import csv
import random
from math import ceil
from math import pi
from math import radians
from math import sqrt
import logging

import rasterio
from rasterio import features
from affine import Affine
import pandas
import numpy.ma as ma
import numpy as np
from skimage.draw import ellipse

from futurefire import util
from futurefire.config import config


log = logging.getLogger(__name__)


def burn_ellipse(r, c, area, image):
    """
    Generate coordinates of pixels within randomly oriented ellipse
    http://scikit-image.org/docs/dev/api/skimage.draw.html#skimage.draw.ellipse
    """
    # create a set of valid minor axis / major axis ratios in 5% increments
    ratios = [
        round((ratio * .01), 2)
        for ratio in range(
            config["fire_axis_ratio_min"], config["fire_axis_ratio_max"], 5
        )
    ]

    # generate axes lengths by randomly choosing a ratio from above and using
    # the area to determine the lengths (Area = pi * a * b)
    ratio = random.choice(ratios)
    a = sqrt((area / pi) / ratio)
    b = a * ratio

    # define random rotation (0-360 degrees in 1 degree increments)
    rotation = random.choice([radians(deg) for deg in range(config["fire_rotation_min"], config["fire_rotation_max"], config["fire_rotation_increment"])])

    # create ellipse
    rr, cc = ellipse(r, c, a, b, image.shape, rotation=rotation)
    return (rr, cc)


def random_index(forest):
    """
    Given a 2d array where 0=non-forest, 1=forest, generate a randomly sorted
    list of 1-d index values where array=1 (forested)
    """
    # random.shuffle works with 1d arrays - flatten the input 2d forest array
    flat_forest = forest.flatten()

    # generate an array of index values for length of flattened mask
    # and return only values that are currently forest
    idx = np.arange(len(flat_forest))[flat_forest == 1]

    # shuffle the index and return
    np.random.shuffle(idx)
    return idx


def apply_fires(firelist, forest_reg, forest_prov, burn_image, runid, region, year, n=None):
    """For a given year, burn a list of fires [(id, area),] into forest_reg,
    burn_image and write to csv
    """
    # if specified, only process n records
    if n:
        firelist = firelist[:n]

    # generate a shuffled index of all cells with forest
    forest_idx = random_index(forest_reg)

    # start from the top of the shuffled list
    idx_position = 0

    # initialize a list to track output burns for writing to csv
    burns = []

    log.info("Processing fires for region {}, year {}".format(region, year))

    flattened = forest_reg.flatten()

    # loop through all fires in list
    for fire in zip(list(firelist["burnid"]), [round(a) for a in list(firelist["area"])]):

        # note id and target burned forest area
        burn_id = fire[0]
        target_area = fire[1]
        log.debug("burn_id: {}, target_area: {}".format(burn_id, target_area))
        # because we are looping through the fires, applying them individually
        # it is necessary to make sure the fire's ignition location has not
        # already burned *this year*

        while flattened[forest_idx[idx_position]] == 0:
            idx_position += 1
            if idx_position > len(forest_idx):
                raise RuntimeError("No unburned area found")

        # convert the resulting index value into a row/column reference -
        # the cell at centre of the ellipse to be burned
        ignition_r, ignition_c = np.unravel_index(
            forest_idx[idx_position], burn_image.shape
        )

        # initialize tracking variables for current individual fire
        # define fire growth increment area based on % provided
        increment = (config["fire_ellipse_pct_growth"] * .01) * target_area
        # start the ellipse size as the target size
        ellipse_area = target_area
        # empty list for holding iterations as the fire grows
        ellipse_list = []
        # track whether the burned forest area as big as the target
        target_area_met = False

        # The ignition point is forested but the fire ellipse may cover many
        # non-forested or previously burned cells. Expand the ellipse until it
        # burns enough forested cells to meet target
        while not target_area_met:

            # create burn ellipse with given area at ignition point
            rr, cc = burn_ellipse(ignition_r, ignition_c, ellipse_area, burn_image)

            # calc current forest area within the created burn ellipse
            burned_forest_area = forest_reg[rr, cc].sum()

            # record the values (iteration, (elipse), burned_area, diff)
            ellipse_list.append(
                {
                    "iteration": len(ellipse_list) + 1,
                    "ellipse": (rr, cc),
                    "burned_forest_area": burned_forest_area,
                    "ellipse_area": ellipse_area,
                    "difference": abs(target_area - burned_forest_area),
                }
            )

            # stop if target met,
            if burned_forest_area >= target_area:
                target_area_met = True
            # bail after 1000 iterations to prevent endless loops
            if len(ellipse_list) > 1000:
                raise RuntimeError("Cannot meet target area")
            # otherwise increment ellipse area
            else:
                ellipse_area = ellipse_area + increment

        # if there was only one iteration, use it
        if len(ellipse_list) == 1:
            result = ellipse_list[0]

        # if the fire grew and we have a list of iterations, extract the last
        # two (one undersized, one oversized) and determine which is closest
        # to the target area
        else:
            result = min(ellipse_list[-2:], key=lambda x: x["difference"])

        # create an image with just the burn ellipse, identify forested within
        # (there is probably a more memory efficent way to do this?)
        burn = np.zeros(shape=burn_image.shape)
        burn[result["ellipse"][0], result["ellipse"][1]] = 1
        burn[forest_reg != 1] = 0

        # apply the burn to the output burned image
        burn_image[burn == 1] = year

        # apply the burn to the regional forest status image
        # (for finding forest for current timestep/region)
        forest_reg[result["ellipse"][0], result["ellipse"][1]] = 0

        # also apply to the provincial forest status image
        # (for tracking forest over time)
        forest_prov[result["ellipse"][0], result["ellipse"][1]] = 0

        # record burn data as dict for dump to tabular format
        # so we can report on individual burns
        # add year, region, runid to
        burns.append(
            {
                "burn_id": burn_id,
                "year": year,
                "runid": runid,
                "region": region,
                "target_area": target_area,
                "iteration": result["iteration"],
                "burned_forest_area": result["burned_forest_area"],
                "ellipse_area": result["ellipse_area"],
            }
        )
        # increment the index to the random 'ignition points'
        idx_position += 1

    return burns


def write_fires(
    runid, year, burn_image, burn_list, out_path, out_csv, burn_year=False
):
    """Write burn image, list of burns to disk
    """
    log.info("Writing burn data to {}".format(out_path))

    # write all burn_id, iteration, burned_forest_area data to csv
    with open(out_csv, "a", newline="") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=[
                "burn_id",
                "year",
                "region",
                "runid",
                "target_area",
                "iteration",
                "burned_forest_area",
                "ellipse_area",
            ],
        )
        writer.writerows(burn_list)

    # a burn_image value of 1 (rather than year) should save some disk space
    if burn_year:
        dtype = "int16"
    else:
        burn_image[burn_image > 0] = 1
        dtype = "uint8"
        burn_image = burn_image.astype(dtype)

    # get output crs, transform etc from the input regions tiff
    with rasterio.open(config["regions"]) as src:
        profile = src.profile

    # output file names are: <runid>_<year>_burns.tif
    filename = "_".join([str(x) for x in [runid, year]])
    burn_tiff = os.path.join(out_path, "{}_burns.tif".format(filename))

    # write the burn image
    with rasterio.open(burn_tiff, "w", **profile) as dst:
        dst.write(burn_image, 1)


def create_salvage(run, year):
    """Read burn tiff and roads buff tiff, overlay
    """
    roads_tiff = os.path.join(config["wksp"], "roads_buf.tif")
    with rasterio.open(roads_tiff) as src:
        roads = src.read(1)

    burns_tiff = os.path.join(config["output"], "run_year_burn.tif")
    with rasterio.open(burns_tiff) as src:
        burns = src.read(1)

    salvage = burns[roads == 1]

    # write salvage to disk
    salvage_tiff = os.path.join(config["output"], "run_year_salvage.tif")
    with rasterio.open(salvage_tiff, "w", **profile) as dst:
        dst.write(salvage, 1)
