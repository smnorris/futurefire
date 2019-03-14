import logging

import click
import pgdata

import futurefire
from futurefire import util
from futurefire.config import config


util.configure_logging()
log = logging.getLogger(__name__)


@click.group()
def cli():
    pass


@cli.command()
def createdb():
    """Create a fresh database / load extensions / create functions
    """
    pgdata.create_db(config["db_url"])
    db = pgdata.connect(config["db_url"])
    db.execute("CREATE EXTENSION postgis")


@cli.command()
@click.option("-v", "--validate", is_flag=True)
@click.argument("config_file", type=click.Path(exists=True))
def load(config_file, validate):
    """Load input data to postgres
    """
    util.load_config(config_file)
    db = pgdata.connect(config["db_url"])
    for layer in ["inventory", "roads"]:
        log.info("Loading {} to postgres".format(layer))
        db.ogr2pg(config["inputs_gdb"], in_layer=config[layer], out_layer=layer)
