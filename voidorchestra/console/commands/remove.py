#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains sub-commands for `molegazer remove`.

These are (mostly) development commands designed to remove the DB
"""
from typing import List
from pathlib import Path

import click
from sqlalchemy.orm import Session

import voidorchestra.db
from voidorchestra.db.image import Image
from voidorchestra.db.stamp import Stamp
from voidorchestra.db.mole import Mole
from molegazer import config
import molegazer.log


logger = molegazer.log.get_logger(__name__.replace(".", "-"))


@click.group()
def remove():
    """Remove files of a given type."""


@remove.command(
    name="database",
    help="Deletes the database."
)
@click.pass_context
def remove_database(ctx: dict) -> None:
    """
    Deletes the database
    """

    database_path: Path = Path(config["PATHS"]["database"])

    if database_path.exists():
        database_path.unlink()

        click.echo(
            f"Deleted database at {database_path}"
        )
    else:
        click.echo(
            f"No database to delete at {database_path}"
        )
