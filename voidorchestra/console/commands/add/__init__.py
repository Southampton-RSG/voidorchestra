#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains sub-commands for `void-orchestra add`.

The commands should add new entries to the DB from a fixture file.
"""
from pathlib import Path

import click
from sqlalchemy.orm import Session

from voidorchestra import config_paths
from voidorchestra.console.commands.add.lightcurve import lightcurve
from voidorchestra.db import connect_to_database_engine
from voidorchestra.db.sonification_method.soundfont import SonificationMethodSoundfont
from voidorchestra.db.sonification_profile import SonificationProfile


@click.group()
def add():
    """
    Add new entities from fixture files.
    """

add.add_command(lightcurve)


@add.command(name="soundfonts")
@click.pass_context
@click.option(
    "-f",
    "--filepath",
    type=click.Path(exists=True),
    default=config_paths["soundfont_fixtures"],
    show_default=True,
    help="A filepath to the soundfont fixtures to add",
)
def add_soundfonts(
        ctx: click.Context,
        filepath: Path,
) -> None:
    """
    Add new soundfonts into Void Orchestra.

    Parameters
    ----------
    filepath:
        Path to the soundfont fixtures to add
    """
    with Session(
        engine := connect_to_database_engine(config_paths["database"]),
        info={"url": engine.url},
    ) as session:
        SonificationMethodSoundfont.load_fixtures(session, filepath)

    if ctx.obj["VERBOSE"] or ctx.obj["DEBUG"]:
        click.echo("New soundfonts successfully added to Void Orchestra")


@add.command(name="profiles")
@click.pass_context
@click.option(
    "-f",
    "--filepath",
    type=click.Path(exists=True),
    default=config_paths["sonification_profile_fixtures"],
    show_default=True,
    help="A filepath to the sonification profile fixtures to add",
)
def add_sonification_profiles(
        ctx: click.Context,
        filepath: Path,
) -> None:
    """
    Add new sonification profiles into Void Orchestra.

    Parameters
    ----------
    filepath:
        Path to the sonification profiles to add
    """
    with Session(
        engine := connect_to_database_engine(config_paths["database"]),
        info={"url": engine.url},
    ) as session:
        SonificationProfile.load_fixtures(session, filepath)

    if ctx.obj["VERBOSE"] or ctx.obj["DEBUG"]:
        click.echo("New sonification profiles successfully added to Void Orchestra")
