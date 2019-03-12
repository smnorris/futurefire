import futurefire
from futurefire.config import config
from futurefire import util


def test_config():
    util.load_config("tests/test_config.cfg")
    assert config["input_gdb"] == "tests/data/data.gdb.zip"


def test_load():
    """ Check that data load is successful
    """
    futurefire.load()
    assert "inventory" in db.tables
