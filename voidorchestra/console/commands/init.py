#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Entry point for the `voidorchestra` command.
"""

from pathlib import Path

import click
from sqlalchemy.orm import Session

import voidorchestra.db


@click.group()
def init() -> None:
    """
    Initialization commands for the Zooniverse Orchestrator

    This group contains commands for initialization of the Zooniverse Sonification DB.
    """


@init.command(name="database")
@click.pass_context
@click.option(
    "--db",
    type=click.Path(),
    default=voidorchestra.config["PATHS"]["database"],
    show_default=True,
    help="The location to write a new database to.",
)
@click.option(
    "--soundfonts",
    type=click.Path(),
    default=voidorchestra.config["PATHS"]["soundfont_fixtures"],
    show_default=True,
    help="The location of the soundfont fixtures CSV to read in.",
)
def init_database(ctx: click.Context, db: str, view: str) -> None:
    """Initialize the MoleDB database."""
    voidorchestra.db.create_new_database(db)
    with Session(voidorchestra.db.connect_to_database_engine(voidorchestra.config["PATHS"]["database"])) as session:
        load_views(session, view)
    if ctx.obj["VERBOSE"] or ctx.obj["DEBUG"]:
        click.echo("New database created successfully")


@init.command(name="soundfonts")
@click.pass_context
@click.option(
    "-f",
    "--filepath",
    type=click.Path(exists=True),
    default=voidorchestra.config["PATHS"]["soundfont_fixtures"],
    show_default=True,
    help="A filepath to the soundfont fixtures to add",
)
def init_views(ctx: click.Context, filepath: str) -> None:
    """Initialize new views into Void Orchestra."""
    with Session(
        engine := voidorchestra.db.connect_to_database_engine(voidorchestra.config["PATHS"]["database"]), info={"url": engine.url}
    ) as session:
        voidorchestra.db.SonificationMethodSoundfont.load_fixtures(session, filepath)

    if ctx.obj["VERBOSE"] or ctx.obj["DEBUG"]:
        click.echo("New soundfonts successfully added to Void Orchestra")
