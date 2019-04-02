# A very crude (but cross platform) batch processing script for
# processing draws in parallel

# For example, process low scenario draws 10-20:
# $ python batch.py low 10 20

# Or, process high scenario for specific draws:
# $ python batch.py high "1 2 5 10 12 13"

# Batch processing for test run was done on 32core 128G Ubuntu 18.04.2
# On this system, a max of 10/11 concurrent processes is possible. At about
# 10G per process the system runs out of memory quickly

# runs
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
        if scenario == "high":
            if draw_min:
                p.map(run_high, range(draw_min, draw_max + 1))
            elif draw_list:
                draws = draw_list.split(" ")
                p.map(run_high, draws)
        elif scenario == "low":
            if draw_min:
                p.map(run_low, range(draw_min, draw_max + 1))
            elif draw_list:
                draws = draw_list.split(" ")
                p.map(run_low, draws)


if __name__ == "__main__":
    batch()
