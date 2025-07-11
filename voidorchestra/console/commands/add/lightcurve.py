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
from voidorchestra.db import connect_to_database_engine
from voidorchestra.db.lightcurve.synthetic import LightcurveSyntheticRegular


@click.group()
@click.pass_context
def lightcurve():
    """
    Add new lightcurves from fixture files.
    """

@lightcurve.command(name="synthetic")
@click.pass_context
@click.option(
    "-f",
    "--filepath",
    type=click.Path(exists=True),
    default=config_paths.get("lightcurve_synthetic_regular_fixture", None),
    show_default=True,
    help="A filepath to the synthetic lightcurve fixtures to add.",
)
def add_lightcurve(
        ctx: click.Context,
        filepath: Path
) -> None:
    """
    Add new synthetic lightcurves with regular frequencies into Void Orchestra.

    Parameters
    ----------
    ctx: click.Context
        Click context
    filepath: Path
        Path to the synthetic lightcurves to add
    """
    if not filepath:
        raise FileNotFoundError("No filepath provided.")

    with Session(
        engine := connect_to_database_engine(config_paths["database"]),
        info={"url": engine.url},
    ) as session:
        LightcurveSyntheticRegular.load_fixtures(session, filepath)

    if ctx.obj["VERBOSE"] or ctx.obj["DEBUG"]:
        click.echo("New synthetic lightcurves successfully added to Void Orchestra")
