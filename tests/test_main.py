import os

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


#def test_rasterize_inventory():
#    with rasterio.open(os.path.join(config["wksp"], "inventory.tif")) as src:
#        image = src.read()
#    futurefire.burn_ellipse(50,50, 100, image)


#def test_burn_ellipse():
#    with rasterio.open(os.path.join(config["wksp"], "inventory.tif")) as src:
#        image = src.read()
#    futurefire.burn_ellipse(50,50, 100, image)

