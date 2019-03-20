# Default config
# To overwrite these values, provide futurefire command with a config file
# See sample_config.cfg

config = {
    "wksp": "wksp",
    "inputs_gdb": "inputs/inputs.gdb",
    "roads": "roads",
    "inventory": "inventory",
    "regions": "inputs/regions.tif",
    "region_lookup": {"Coast": 1, "Northern Interior": 2, "Southern Interior": 3},
    # bounds are  "xmin ymin xmax ymax" in target area preserving projection
    # (EPSG:3005, BC Albers)
    "bounds": "159587.5 173787.5 1881187.5 1748187.5",
    # buffer and cell size are m
    "buffer": 500,
    "cell_size": 100,
    "fire_axis_ratio_min": 20,
    "fire_axis_ratio_max": 80,
    # increasing the pct growth reduces iterations and processing time
    "fire_ellipse_pct_growth": 1,
    "regen": 10,
    "outputs": "outputs",
    "log_file": "futurefire.log",
}
