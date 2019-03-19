# simple scenario - 1 run, 1 region, 1 year, 1 fire
xsv search -s runid ^1$ ../data/lowscenario.csv | xsv search -s region ^Coast$ | xsv search -s year ^2021$ > ../tests/scenario_1.csv

# 1 run, 1 region, 1 year, several fires
xsv search -s runid ^1$ ../data/lowscenario.csv | xsv search -s region ^Coast$ | xsv search -s year ^2022$ > ../tests/scenario_2.csv

# 1 run, 1 region, several years
xsv search -s runid ^1$ ../data/lowscenario.csv | xsv search -s region ^Coast$ | xsv search -s year ^202[1,2,3,4] > ../tests/scenario_3.csv