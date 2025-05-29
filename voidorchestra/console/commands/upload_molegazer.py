#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains sub-commands for `molegazer upload`.

The commands should upload data into MoleDB from the perspective of MoleGazer.
"""
from typing import Optional

import click

from molegazer import config
import molegazer.process.images


@click.group()
def upload():
    """Input existing data into MoleDB"""


@upload.command(
    name="images",
    help="Inputs the files in the config file's PATHS:images_new directory into the database."
)
@click.pass_context
@click.option(
    "-d",
    "--directory",
    nargs=1,
    type=click.Path(dir_okay=True, exists=True),
    default=None,
    help="An optional path to the directory to upload."
)
def upload_images(ctx: dict, directory: Optional[str] = None) -> None:
    """
    Input new files from a directory.

    Inputs the files in the config file's PATHS:images_new directory into the database.

    Parameters
    ----------
    directory: Optional[str]
        If provided, a directory to upload data from (that is not the default one)
    """
    if not directory:
        directory = config['PATHS']['images_new']
    elif directory == config['PATHS']['images_new']:
        click.echo(
            "Warning: Directory passed with `-d` is the same as the default directory!"
        )

    molegazer.process.images.upload_images(directory)

    if ctx.obj["VERBOSE"] or ctx.obj["DEBUG"]:
        click.echo(f"Imported image files")
