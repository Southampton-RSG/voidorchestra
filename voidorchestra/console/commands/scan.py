#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains sub-commands for `molegazer scan`.

These are (mostly) development commands designed to scan parameter space
"""
from pathlib import Path
from typing import Tuple, Optional

import click
from sqlalchemy.orm import Session

import voidorchestra.db
from voidorchestra.db.image import Image
from molegazer import config
from molegazer.process.scan import sweep_param_space


@click.command(
    name="scan",
    help="Given a setting for the mole detection from the parameters file, produces figures that demonstrate "
         "the outcome of changing the values across that range. Takes three arguments - the name of the parameter "
         "to scan over, and the minimum and maximum values to scan (inclusive)."
)
@click.pass_context
@click.argument(
    "test-param", type=str, nargs=1,
    # help="The parameter of the detection algorithm to test, e.g. 'threshold', 'min sigma'."
)
@click.argument(
    "test-range", type=float, nargs=2,
    # help="The minimum and maximum values of that parameter to test, inclusive."
)
@click.option(
    "-s",
    "--test-steps",
    nargs=1,
    type=int,
    default=5,
    # help="The number of steps in the parameter range to try.",
)
@click.option(
    "-i",
    "--image-id",
    nargs=1,
    type=int,
    default=None,
    help="An optional image ID for the threshold sweep to be performed on."
)
@click.option(
    "-n",
    "--image-name",
    nargs=1,
    type=str,
    default=None,
    help="An optional image name in the format <PATIENT_NAME>_<YYYYMMDD> for the threshold sweep to be performed on."
)
@click.option(
    "-f",
    "--blob-file",
    nargs=1,
    type=click.Path(exists=True, dir_okay=False, file_okay=True),
    default=None,
    help="An optional path to the output of a previous scan to avoid redoing image-recognition. "
         "Only used when testing params from the 'FILTERING' section."
)
def scan(
        ctx: dict, test_param: str, test_range: Tuple[float, float],
        test_steps: int = 5,
        image_id: Optional[int] = None,
        image_name: Optional[str] = None,
        blob_file: Optional[Path] = None
) -> None:
    """
    Given a parameter, produces figures that demonstrate the outcome of changing
    the values across that range.

     Parameters
    ----------
    test_param: str
        The parameter of the detector to test, e.g. 'blob_threshold', 'surroundings_difference_min'.
    test_range: Tuple[float, float]
        The minimum and maximum values of that parameter to test.
    test_steps: int, default 5
        The number of steps in that range, endpoints inclusive.
    image_id: Optional[int]
        If we want to test on a single specific image, what is its ID?
        Otherwise, tests on the first image in the DB.
    image_name: Optional[str]
        If we want to test on a specific image, what's it's name? (<PATIENT_ID>_MM_DD_YYYY_<BODYPART ID>)
    blob_file: Optional[Path]
        An optional path to the output of a previous scan to avoid redoing the image-recognition,
        for tests of filtering options
    """
    with Session(
        engine := voidorchestra.db.connect_to_database_engine(config["PATHS"]["database"])
    ) as session:
        if image_id and image_name:
            raise FileNotFoundError("You have specified both an ID and a name - you can only specify one.")
        elif image_name:
            image: Image = session.query(Image).filter(Image.image_name == image_name).first()
        elif image_id:
            image: Image = session.query(Image).get(image_id)
        else:
            image: Image = session.query(Image).first()

        if blob_file and 'surroundings' not in test_param:
            click.echo(f"Sweeping parameter '{test_param}' requires rerunning the image recognition algorithm.")
            exit()

        sweep_param_space(
            image=image,
            test_param=test_param,
            test_param_steps=test_steps,
            test_param_range=test_range,
            blob_file=blob_file
        )

    if ctx.obj["VERBOSE"] or ctx.obj["DEBUG"]:
        click.echo(f"Scanned parameter space")
