# Default config
# To overwrite these values, provide futurefire command with a config file
# See sample_config.cfg

config = {
    "wksp": "data",
    "inputs_gdb": "data/inputs.gdb",
    "roads": "roads",
    "inventory": "inventory",
    "regions": "data/regions.tif",
    "region_lookup":
        {
            1: "Coast",
            2: "Northern Interior",
            3: "Southern Interior"
        },
    "buffer": 500,
    "cell_size": 100,
    "fire_axis_ratio_min": 20,
    "fire_axis_ratio_max": 80,
    "regen": 10,
    "outputs": "outputs",
    "log_file": "futurefire.log"
}
