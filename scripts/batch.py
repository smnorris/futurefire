# A very crude batch processing script for processing draws in parallel

# For example, process low scenario draws 10-20:
# $ python batch.py low 10 20

# Or, process high scenario for specific draws:
# $ python batch.py high "1 2 5 10 12 13"


import subprocess
from multiprocessing import Pool
import click


def run_low(runid):
    cmd = ["futurefire", "burn", "inputs/lowscenario.csv", "--runid", str(runid)]
    subprocess.run(cmd)


def run_high(runid):
    cmd = ["futurefire", "burn", "inputs/highscenario.csv", "--runid", str(runid)]
    subprocess.run(cmd)


@click.command()
@click.argument("scenario")
@click.option("--draw_min", type=click.INT)
@click.option("--draw_max", type=click.INT)
@click.option("--draw_list")
@click.option("-n", "--n_cores", default=10)
def batch(scenario, draw_min, draw_max, draw_list, n_cores):
    with Pool(n_cores) as p:
        if draw_min and scenario == "high":
            p.map(run_high, range(draw_min, draw_max + 1))
        elif draw_min and scenario == "low":
            p.map(run_low, range(draw_min, draw_max + 1))
        elif draw_list:
            draws = draw_list.split(" ")
            p.map(run_low, draws)


if __name__ == "__main__":
    batch()
