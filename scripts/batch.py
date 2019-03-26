from subprocess import Popen

cmds = []
for i in range(1, 101):
    cmds.append(["futurefire", "burn", "inputs/lowscenario.csv", "--runid", i])

procs_list = [Popen(cmd) for cmd in cmds]
for proc in procs_list:
    proc.wait()
