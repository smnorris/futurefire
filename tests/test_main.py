import os
import pandas as pd
import numpy as np

import futurefire
from futurefire.config import config
from futurefire import util


def test_config():
    util.load_config(os.path.join(os.path.dirname(__file__), 'test.cfg'))
    assert config["inputs_gdb"] == "tests/data/data.gdb.zip"
    assert config["region_lookup"] == {
            "Coast": 1,
            "Northern Interior": 2,
            "Southern Interior": 3
        }
    assert config["outputs"] == "tests/outputs"
    assert config["bounds"][0] == "1368548"
    assert config["fire_ellipse_pct_growth"] == 2


def test_burn_ellipse():
    array = np.zeros(shape=[100, 100])
    rr, cc = futurefire.burn_ellipse(5, 5, 10, array)
    array[rr, cc] = 1
    # not exactly a precise test, but area should be within 20/30%
    assert array.sum() >= 7 and array.sum() <= 13


def test_apply_one_fire(tmpdir):
    firelist = pd.read_csv(os.path.join(os.path.dirname(__file__),"scenario_1.csv"))

    # create a 100x100 image of 75% forest
    forest_image = np.zeros([100, 100])
    random_flat = np.random.choice(10000, 7500, replace=False)
    random_forest_idx = np.unravel_index(random_flat, forest_image.shape)
    forest_image[random_forest_idx] = 1

    # initialize a burn image of the same shape
    burn_image = np.zeros(forest_image.shape)

    # apply fire
    out_csv = tmpdir.join("burned.csv")
    futurefire.apply_fires(firelist, forest_image, forest_image, burn_image)
    # assert that csv / burn / forest all have correct sums


def test_apply_several_fires(tmpdir):
    firelist = pd.read_csv(os.path.join(os.path.dirname(__file__),"scenario_2.csv"))

    # create a 100x100 image of 75% forest
    forest_image = np.zeros([1000, 1000])
    random_flat = np.random.choice(1000000, 800000, replace=False)
    random_forest_idx = np.unravel_index(random_flat, forest_image.shape)
    forest_image[random_forest_idx] = 1

    # initialize a burn image of the same shape
    burn_image = np.zeros(forest_image.shape)

    # apply fire
    out_csv = tmpdir.join("burned.csv")
    futurefire.apply_fires(firelist, forest_image, forest_image, burn_image)
    # assert that csv / burn / forest all make sense


def test_regen():

    from futurefire.config import config

    # construct a small dummy scenario
    config["region_lookup"] = {1: 1, 2: 2}
    config["regen"] = 3

    # 4 years of fires, 2 regions, 1 ha per burn
    fires_df = pd.DataFrame.from_dict(
        {'runid':  [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
         'region': [1, 2, 1, 2, 1, 2, 1, 2, 1, 2],
         'year':   [10, 10, 11, 11, 12, 12, 13, 13, 14, 14],
         'burnid': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
         'area':   [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]}
    )

    runid = 1
    regions = sorted(list(fires_df.region.unique()))
    years = sorted(list(fires_df.year.unique()))

    # 6 x 6 forest checkerboard, 1/2 forest, 1/2 non forested.
    forest_image = np.ones([6, 6])
    forest_image[:3, :3] = 0
    forest_image[3:, 3:] = 0

    # two regions, 1 and 2
    regions = [1, 2]
    regions_image = np.ones([6, 6])
    regions_image[3:] = 2

    # initialize output burned year raster
    burn_image = np.zeros(shape=forest_image.shape)

    # apply annual burns
    for year in years:
        fires = fires_df[fires_df["year"] == year]
        burn_list = futurefire.burn_year(fires, regions, forest_image, regions_image, burn_image)

    # check that burned areas add up as expected (1ha per year => 9ha)
    # the area is not exact because of randomnes of ellipses
    assert len(burn_image[burn_image > 0]) >= 9

    # check that regen wored (at year=14, cells burned at year 11 are now 1)
    assert int(np.unique(forest_image[burn_image == 11])) == 1


def test_fail():

    from futurefire.config import config

    # construct a small dummy scenario
    config["region_lookup"] = {1: 1, 2: 2}
    config["regen"] = 3

    # 4 years of fires, 2 regions, 1 ha per burn
    fires_df = pd.DataFrame.from_dict(
        {'runid':  [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
         'region': [1, 2, 1, 2, 1, 2, 1, 2, 1, 2],
         'year':   [10, 10, 11, 11, 12, 12, 13, 13, 14, 14],
         'burnid': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
         'area':   [1, 4, 1, 4, 1, 1, 1, 1, 1, 5]}
    )

    runid = 1
    regions = sorted(list(fires_df.region.unique()))
    years = sorted(list(fires_df.year.unique()))

    # 10 x 10 forest checkerboard, 1/2 forest, 1/2 non forested.
    forest_image = np.ones([6, 6])
    forest_image[:3, :3] = 0
    forest_image[3:, 3:] = 0

    # two regions, 1 and 2
    regions = [1, 2]
    regions_image = np.ones([6, 6])
    regions_image[3:] = 2

    # initialize output burned year raster
    burn_image = np.zeros(shape=forest_image.shape)

    # apply annual burns
    for year in years:
        fires = fires_df[fires_df["year"] == year]
        burn_list = futurefire.burn_year(fires, regions, forest_image, regions_image, burn_image)

    # check that burned areas add up as expected (1ha per year => 9ha)
    # the area is not exact because of randomnes of ellipses
    assert len(burn_image[burn_image > 0]) >= 9

    # check that regen wored (at year=14, cells burned at year 11 are now 1)
    assert int(np.unique(forest_image[burn_image == 11])) == 1
