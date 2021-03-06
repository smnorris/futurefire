import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


# Parse the version
with open("futurefire/__init__.py", "r") as f:
    for line in f:
        if line.find("__version__") >= 0:
            version = line.split("=")[1].strip()
            version = version.strip('"')
            version = version.strip("'")
            break

requires = ["pandas", "gdal", "scikit-image", "rasterio", "click", "numpy"]

test_requirements = ["pytest"]

setup(
    name="futurefire",
    version=version,
    url="https://github.com/smnorris/futurefire",
    description=u"Randomly generate burned areas for future fire scenarios",
    long_description=read("README.md"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    keywords="NRCAN CBM-CFS3 mitigation fires",
    author=u"Simon Norris",
    author_email="snorris@hillcrestgeo.ca",
    license="Apache",
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
    tests_require=test_requirements,
    entry_points="""
      [console_scripts]
      futurefire=futurefire.cli:cli
      """,
)
