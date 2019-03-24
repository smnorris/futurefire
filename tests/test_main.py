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
    futurefire.apply_fires(firelist, forest_image, burn_image, 1, 'Region', 2021)
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
    futurefire.apply_fires(firelist, forest_image, burn_image, 1, 'Region', 2021)
    # assert that csv / burn / forest all make sense


def test_apply_yearly_fires(tmpdir):
    fires_df = pd.read_csv(os.path.join(os.path.dirname(__file__),"scenario_3.csv"))

    years = sorted(list(fires_df.year.unique()))

    # create a 100x100 image of 75% forest
    forest_image = np.zeros([1000, 1000])
    random_flat = np.random.choice(1000000, 800000, replace=False)
    random_forest_idx = np.unravel_index(random_flat, forest_image.shape)
    forest_image[random_forest_idx] = 1

    # initialize a burn image of the same shape
    burn_image = np.zeros(forest_image.shape)

    # apply fire
    out_csv = tmpdir.join("burned.csv")

    for year in years:
        futurefire.apply_fires(fires_df, forest_image, burn_image, 1, 'Region,', year)

    # assert that csv / burn / forest all make sense


def test_regen():
    # test that regen logic works by burning 2 cells per year in 4 cell grid
    config["regen"] = 1
    fires = pd.DataFrame.from_dict({'burnid': [1,], 'area': [2,]})
    years = [2020, 2021, 2022]
    forest_image = np.ones([2, 2])
    burn_image = np.zeros(forest_image.shape)
    for year in years:
        futurefire.apply_fires(fires, forest_image, burn_image, 1, 'Region,', year)
        forest_image[burn_image == (year - config["regen"])] = 1
    assert forest_image.sum() == 2
