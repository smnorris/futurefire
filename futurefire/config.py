# Default config
# To overwrite these values, provide futurefire command with a config file

config = {
    "db_url": "postgresql://postgres:postgres@localhost:5432/futurefire",
    "roads": "roads",
    "high_scenario": "data/HighScenario.csv",
    "low_scenario": "data/LowScenario.csv",
    "inputs_gdb": "data/inputs.gdb",
    "inventory": "inventory",
    "buffer": 100,
    "cell_size": 50,
    "outputs": "outputs",
    "log_file": "futurefire.log",
}
