# a very crude batch processing script

# EG process low scenario draws 10-20 in parallel:
# $ python batch.py low 10 20
import subprocess
from multiprocessing import Pool
import os
import click


def run_low(runid):
    cmd = ["futurefire", "burn", "inputs/lowscenario.csv", "--runid", str(runid)]
    subprocess.run(cmd)


def run_high(runid):
    cmd = ["futurefire", "burn", "inputs/highscenario.csv", "--runid", str(runid)]
    subprocess.run(cmd)


@click.command()
@click.argument("scenario")
@click.argument("draw_min")
@click.argument("draw_max")
def batch(scenario, draw_min, draw_max):
    with Pool(os.cpu_count() - 1) as p:
        if scenario == "high":
            p.map(run_high, range(draw_min, draw_max + 1))
        if scenario == "low":
            p.map(run_low, range(draw_min, draw_max + 1))


if __name__ == "__main__":
    batch()
