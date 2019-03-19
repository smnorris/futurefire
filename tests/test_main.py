import os
import numpy as np

import futurefire
from futurefire.config import config
from futurefire import util


def test_config():
    util.load_config(os.path.join(os.path.dirname(__file__), 'test_config.cfg'))
    assert config["inputs_gdb"] == "tests/data/data.gdb.zip"
    assert config["region_lookup"] == {
            1: "Coast",
            2: "Northern Interior",
            3: "Southern Interior"
        }
    assert config["outputs"] == "tests/outputs"
    assert config["bounds"][0] == "1368548"


def test_burn_ellipse():
    array = np.zeros(shape=[10, 10])
    rr, cc = futurefire.burn_ellipse(5, 5, 10, array)
    array[rr, cc] = 1
    # not exactly a precise test, but area should be within 20%
    assert array.sum() >= 8 and array.sum() <= 13

