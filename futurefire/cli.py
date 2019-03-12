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
def load():
    """Load input data to postgres
    """
    db = pgdata.connect(config["db_url"])

    for layer in ["inventory", "roads"]:
        db.ogr2pg(
            config["input_gdb"],
            in_layer=config[layer],
            out_layer=layer
        )
