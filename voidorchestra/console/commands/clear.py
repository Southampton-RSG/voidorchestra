#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains sub-commands for `molegazer clear`.

These are (mostly) development commands designed to clear the DB of content to easily test re-generation
"""
import logging
from typing import List
from pathlib import Path

import click
from sqlalchemy.orm import Session

import voidorchestra.db
from voidorchestra import config
import voidorchestra.log
from voidorchestra.db import Sonification

logger: logging.Logger = voidorchestra.log.get_logger(__name__.replace(".", "-"))


@click.group()
def clear():
    """Clear data of a given kind from Void Orchestra's database."""


@clear.command(
    name="sonifications",
    help="Clears generated sonifications from the database, and deletes the files."
)
@click.pass_context
@click.option(
    "-h",
    "--hard",
    is_flag=True,
    default=False,
    help="Whether to fully clear the output directory, even if there is no DB"
)
def clear_sonifications(ctx: dict, hard: bool = False) -> None:
    """
    Clear image files that have been uploaded.

    Clears uploaded sonifications from the database, and deletes the files.

    Parameters
    ----------
    hard: bool
        Whether to process images that are not in the database (or if there is no database)
    """

    directory_output: Path = Path(config["PATHS"]["output"])

    try:
        with Session(
            engine := voidorchestra.db.connect_to_database_engine(config["PATHS"]["database"])
        ) as session:

            sonifications: List[Sonification] = session.query(Sonification).all()  # This bit is only here to type-hint for the IDE
            num_sonifications_deleted: int = 0

            for sonification in sonifications:
                if sonification.filepath_audio and (directory_output / sonification.filepath_audio).exists():
                    # These catches allow for the possibility that the upload process was broken and created file-less images

                    (directory_output / sonification.filepath_audio).unlink()
                    (directory_output / sonification.filepath_video).unlink()

                num_sonifications_deleted += 1
                logger.debug(
                    f"Deleting sonification {sonification}\n"
                )
                session.delete(sonification)
                session.commit()

        if ctx.obj["VERBOSE"] or ctx.obj["DEBUG"]:
            click.echo(f"Cleared {num_sonifications_deleted} sonifications from database")

    except Exception as e:
        click.echo(f"Could not connect to database: {e}")

    if hard:
        num_sonifications_deleted: int = 0
        for path_sonification in directory_output.rglob('*.mp*'):
            path_sonification.unlink()

            num_sonifications_deleted += 1

        click.echo(
            f"Deleted {num_sonifications_deleted} sonification files not in database"
        )
