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
    rotation = random.choice([radians(deg) for deg in range(1, 360, 1)])

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


def apply_fires(firelist, forest_image, burn_image, year, n=None):
    """Burn a list of fires [(id, area),] into forest_image, burn_image and
    write to csv
    """
    # if specified, only process n records
    if n:
        firelist = firelist[:n]

    # generate a shuffled index of all cells with forest
    forest_idx = random_index(forest_image)

    # start from the top of the shuffled list
    idx_position = 0

    # initialize a list to track output burns for writing to csv
    burns = []

    # loop through all fires in list
    for fire in zip(
        list(firelist.burnid), [round(a) for a in list(firelist.area)]
    ):

        # note id and target burned forest area
        burn_id = fire[0]
        target_area = fire[1]

        # because we are looping through the fires, applying them individually
        # it is necessary to make sure the fire's ignition location has not
        # already burned *this year*
        flattened = forest_image.flatten()
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
        # count the iterations of fire growth
        iteration = 1
        # define fire growth increment area based on % provided
        increment = (pct_growth * .01) * target_area
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
            rr, cc = burn_ellipse(ignition_r, ignition_c, ellipse_area, burned_image)

            # calc current forest area within the created burn ellipse
            burned_forest_area = forest_image[rr, cc].sum()

            # record the values (iteration, (elipse), burned_area, diff)
            ellipse_list.append(
                {
                    "iteration": iteration,
                    "ellipse": (rr, cc),
                    "burned_forest_area": burned_forest_area,
                    "difference": abs(target_area - burned_forest_area)
                }
            )

            # stop if target met, otherwise increment ellipse area
            if burned_forest_area >= target_area:
                target_area_met = True
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

        # apply the burn to the output burned image
        # todo - forested areas only
        burn_image[result["ellipse"][0], result["ellipse"][1]] = year

        # apply the burn to the forest status image
        forest_image[result["ellipse"][0], result["ellipse"][1]] = 0

        # record burn data as dict for dump to tabular format
        # so we can report on individual burns
        burns.append(
            {
                "burn_id": burn_id,
                "iteration": result["iteration"],
                "burned_forest_area": result["burned_forest_area"]
            }
        )
        # increment the index to the random 'ignition points'
        idx_position += 1

    # append burns to out_csv
    with open(config["out_csv"], 'a', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=burns[0].keys())
        writer.writerows(burns)
