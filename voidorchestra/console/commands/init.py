#!/usrStraight copy-paste of file from previosu code/bin/env python3
# -*- coding: utf-8 -*-
"""
Entry point for the `voidorchestra` command.
"""

from pathlib import Path

import click
from click import Context

from voidorchestra import config_paths
from voidorchestra.db import create_new_database


@click.group()
def init() -> None:
    """
    Initialization commands for the Zooniverse Orchestrator

    This group contains commands for initialization of the Zooniverse Sonification DB,
    and commands for initialising DB entities from fixture files.
    """


@init.command(name="database")
@click.pass_context
@click.option(
    "--db",
    type=click.Path(),
    default=config_paths["database"],
    show_default=True,
    help="The location to write a new database to.",
)
def init_database(
    ctx: Context,  # noqa: D417
    db: Path,
) -> None:
    """
    Initialize the Void Orchestra database.

    Parameters
    ----------
    db: Path
        Path to the database location
    """
    create_new_database(db)
    if ctx.obj["VERBOSE"] or ctx.obj["DEBUG"]:
        click.echo("New database created successfully")
