#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains sub-commands for `void-orchestra add`.

The commands should add new entries to the DB from a fixture file.
"""

from pathlib import Path
from typing import List

import click
from click import Context
from panoptes_client import Project as PanoptesProject, Workflow as PanoptesWorkflow
from sqlalchemy.orm import Session

from voidorchestra import config_paths
from voidorchestra.console.commands.input.lightcurve import lightcurve
from voidorchestra.db import connect_to_database_engine
from voidorchestra.db.sonification_method.soundfont import SonificationMethodSoundfont
from voidorchestra.db.sonification_profile import SonificationProfile


@click.group()
def input():
    """
    Add new entities from fixture files.
    """


input.add_command(lightcurve)


@input.command(name="soundfonts")
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
    ctx: Context,  # noqa: D417
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


@input.command(name="profiles")
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
    ctx: Context,  # noqa: D417
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
        sonification_profiles: List[SonificationProfile] = SonificationProfile.load_fixtures(session, filepath)

    if ctx.obj["VERBOSE"] or ctx.obj["DEBUG"]:
        click.echo(f"{len(sonification_profiles)} sonification profiles successfully added to Void Orchestra")
