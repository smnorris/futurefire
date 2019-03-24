import os
import configparser
import logging
import logging.handlers

from futurefire.config import config

log = logging.getLogger(__name__)


def make_sure_path_exists(path):
    """Make directories in path if they do not exist.
    Modified from http://stackoverflow.com/a/5032238/1377021
    :param path: string
    """
    try:
        os.makedirs(path)
    except:
        pass


def load_config(config_file):
    """Read provided config file, overwriting default config values
    """
    log.info("Loading config from file: %s", config_file)
    cfg = configparser.ConfigParser()
    cfg.read(config_file)
    cfg_dict = dict(cfg["CONFIG"])

    # split the bounds string into a list
    if "bounds" in cfg_dict.keys():
        cfg_dict["bounds"] = [b for b in cfg_dict["bounds"].split()]

    if "REGION_LOOKUP" in cfg.keys():
        region_lookup = dict(cfg["REGION_LOOKUP"])
        region_lookup = {k: int(v) for (k, v) in region_lookup.items()}
        cfg_dict["region_lookup"]: region_lookup

    # convert int values to ints
    int_keys = ["buffer","cell_size","fire_axis_ratio_min","fire_axis_ratio_max","fire_rotation_min","fire_rotation_max","fire_rotation_increment","fire_ellipse_pct_growth","regen"]
    for key in int_keys:
        if key in cfg_dict.keys():
            cfg_dict[key] = int(cfg_dict[key])

    # add region lookup dict to main config dict
    for key in cfg_dict:
        config[key] = cfg_dict[key]


def configure_logging():
    logger = logging.getLogger()
    formatter = logging.Formatter("%(asctime)s %(name)-12s %(levelname)-8s %(message)s")
    logger.setLevel(logging.INFO)

    streamhandler = logging.StreamHandler()
    streamhandler.setFormatter(formatter)
    streamhandler.setLevel(logging.INFO)
    logger.addHandler(streamhandler)

    filehandler = logging.handlers.TimedRotatingFileHandler(
        config["log_file"], when="D", interval=7, backupCount=10
    )
    filehandler.setFormatter(formatter)
    filehandler.setLevel(logging.INFO)
    logger.addHandler(filehandler)
