import subprocess
from multiprocessing import Pool
import os


def run(runid):
    cmd = ["futurefire", "burn", "inputs/lowscenario.csv", "--runid", str(runid)]
    subprocess.run(cmd)


if __name__ == '__main__':
    with Pool(os.cpu_count() - 1) as p:
        p.map(run, range(1, 5))
