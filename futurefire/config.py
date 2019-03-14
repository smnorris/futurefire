# Default config
# To overwrite these values, provide futurefire command with a config file

config = {
    "db_url": "postgresql://postgres:postgres@localhost:5432/futurefire",
    "inputs_gdb": "data/inputs.gdb",
    "roads": "roads",
    "inventory": "inventory",
    "high_scenario": "data/HighScenario.csv",
    "low_scenario": "data/LowScenario.csv",
    "buffer": 100,
    "cell_size": 50,
    "outputs": "outputs",
    "log_file": "futurefire.log",
}
