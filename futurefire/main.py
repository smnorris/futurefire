import os
import csv
import random
from math import pi
from math import radians
from math import sqrt
import logging

import rasterio
from rasterio.warp import reproject
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
    rotation = random.choice(
        [
            radians(deg)
            for deg in range(
                config["fire_rotation_min"],
                config["fire_rotation_max"],
                config["fire_rotation_increment"],
            )
        ]
    )

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


def apply_fires(
    firelist, forest_reg, forest_image, burn_image, runid, region, year, n=None
):
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
    burns_list = []

    log.info("Processing - runid:{} region:{} year:{}".format(runid, region, year))

    flattened = forest_reg.flatten()

    # loop through all fires in list
    for fire in zip(
        list(firelist["burnid"]), [round(a) for a in list(firelist["area"])]
    ):

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

            # otherwise increment ellipse area
            elif len(ellipse_list) < 1000:
                if len(ellipse_list) <= 100:
                    increment = (config["fire_ellipse_pct_growth"] * .01) * target_area
                # double the pct_growth increment for iterations 100-500
                elif len(ellipse_list) > 100 and len(ellipse_list) <= 500:
                    increment = (
                        config["fire_ellipse_pct_growth"] * 2 * .01
                    ) * target_area

                # quadruple the pct_growth increment for iterations 500-1000
                elif len(ellipse_list) > 500:
                    increment = (
                        config["fire_ellipse_pct_growth"] * 4 * .01
                    ) * target_area

                ellipse_area = ellipse_area + increment

            # after 1000 expansions, give up and restart burn in another spot
            elif len(ellipse_list) >= 1000:
                log.info(
                    "Cannot meet target area for given ignition point, generating a new one".format()
                )
                # get new ignition point
                idx_position += 1
                ignition_r, ignition_c = np.unravel_index(
                    forest_idx[idx_position], burn_image.shape
                )
                ellipse_area = target_area
                ellipse_list = []

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
        forest_image[result["ellipse"][0], result["ellipse"][1]] = 0

        # record burn data as dict for dump to tabular format
        # so we can report on individual burns
        # add year, region, runid to
        burns_list.append(
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

    return burns_list


def write_fires(
    runid, year, burn_image, burn_list, out_path, out_csv, src_profile, dst_profile
):
    """Write burn image, list of burns to disk
    """
    log.info("Writing - runid:{} year:{}".format(runid, year))

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

    # record burn_image value of 1 rather than year to keep things simple
    # (but retain the burn_image with years for tracking regen)
    burn_ones = np.zeros(burn_image.shape, dtype="uint8")
    burn_ones[burn_image == year] = 1

    # read road buffer and thlb
    roads_tiff = os.path.join(config["wksp"], "roads_buf.tif")
    thlb_tiff = os.path.join(config["wksp"], "thlb.tif")
    with rasterio.open(roads_tiff) as src:
        roads_image = src.read(1)
    with rasterio.open(thlb_tiff) as src:
        thlb_image = src.read(1)

    # create salvage where burn = 1, thlb = 1 and (road = 1 or road = 0)
    # (road buffer has value 0 for road location and 255 for nodata,
    # it might be worth making it a simple 1/0 raster in the load process)
    salvage_image = np.zeros(burn_ones.shape, dtype="uint8")
    salvage_image[(roads_image <= 1) & (burn_ones == 1) & (thlb_image == 1)] = 1

    # write to drawNNN/burn_YYYY , salvage_YYYY
    folder = "draw" + str(runid).zfill(3)

    burn_tiff = os.path.join(out_path, folder, "burn_" + str(year) + ".tif")
    salvage_tiff = os.path.join(out_path, folder, "salvage_" + str(year) + ".tif")

    util.make_sure_path_exists(os.path.join(out_path, folder))

    # define output raster profile based on template (dst)
    out_kwargs = src_profile.copy()
    out_kwargs.update(
        crs=dst_profile["crs"],
        transform=dst_profile["transform"],
        width=dst_profile["width"],
        height=dst_profile["height"],
    )

    # Adjust block size if necessary.
    if "blockxsize" in out_kwargs and out_kwargs["width"] < out_kwargs["blockxsize"]:
        del out_kwargs["blockxsize"]
    if "blockysize" in out_kwargs and out_kwargs["height"] < out_kwargs["blockysize"]:
        del out_kwargs["blockysize"]

    with rasterio.open(burn_tiff, "w", **out_kwargs) as dst:
        reproject(
            source=burn_ones,
            destination=rasterio.band(dst, 1),
            src_transform=src_profile["transform"],
            src_crs=src_profile["crs"],
            dst_transform=out_kwargs["transform"],
            dst_crs=out_kwargs["crs"],
            resampling=0,
            num_threads=1,
        )

    with rasterio.open(salvage_tiff, "w", **out_kwargs) as dst:
        reproject(
            source=salvage_image,
            destination=rasterio.band(dst, 1),
            src_transform=src_profile["transform"],
            src_crs=src_profile["crs"],
            dst_transform=out_kwargs["transform"],
            dst_crs=out_kwargs["crs"],
            resampling=0,
            num_threads=1,
        )


def burn_year(
    fires_df, runid, year, regions, forest_image, regions_image, burn_image, n=None
):
    """Loop through regions, applying all fires for given year and returning
    a list of all the fires burned
    """
    burn_list = []

    for region in regions:

        # get fires for given region/runid/year combo
        fires = fires_df[
            (fires_df["region"] == region)
            & (fires_df["runid"] == runid)
            & (fires_df["year"] == year)
        ]
        # initialize forest for region of interest
        forest_reg = forest_image.copy()
        forest_reg[regions_image != config["region_lookup"][region]] = 0

        # create burns
        burn_list = burn_list + apply_fires(
            fires, forest_reg, forest_image, burn_image, runid, region, year, n=n
        )

    # set forest=1 where it has been regen years since burned
    forest_image[burn_image == (year - config["regen"])] = 1

    return burn_list
