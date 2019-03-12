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
def create_db():
    """Create a fresh database / load extensions / create functions
    """
    pgdata.create_db(config["db_url"])
    db = pgdata.connect(config["db_url"])
    db.execute("CREATE EXTENSION postgis")
