#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains sub-commands for `molegazer create`.

These are (mostly) development commands designed to clear the DB of content to easily test re-generation
"""
from pathlib import Path
from typing import List

import click
from sqlalchemy.orm import Session

import voidorchestra.db
from voidorchestra.db.image import Image
from voidorchestra.db.stamp import Stamp
from molegazer import config
from molegazer.process.stamps import generate_stamps_single
from molegazer.process.context import generate_stamps_context


@click.group()
def create():
    """Create entities within the database"""


@create.command(
    name="stamps",
    help="Create stamps for images that have not yet been scanned."
)
@click.option(
    "-t",
    "--test",
    is_flag=True,
    default=False,
    help="Whether to only create stamps, not contexts, for test purposes."
)
@click.pass_context
def create_stamps(ctx: dict, test: bool = False) -> None:
    """
    Create stamps for images that have not yet been scanned.

     Parameters
    ----------
    test: bool
        Whether or not to only re-generate a single stamp, and not bother to do contexts.
        Also writes intermediate image stages out as tests.
    """

    with Session(
        engine := voidorchestra.db.connect_to_database_engine(config["PATHS"]["database"])
    ) as session:
        if test:
            images: List[Image] = session.query(Image).all()
            generate_stamps_single(session=session, images=[images[0]], test=True)

        else:
            images: List[Image] = session.query(Image).filter_by(date_processed=None).all()

            if images:
                stamps: List[Stamp] = generate_stamps_single(session=session, images=images)
                generate_stamps_context(session=session, stamps=stamps)
            else:
                click.echo("No un-processed images in database!")

    if ctx.obj["VERBOSE"] or ctx.obj["DEBUG"]:
        click.echo(f"Generated new stamps from database")

@create.command(
    name="context",
    help="Generates context stamps for those that don't have any by default, "
         "or optionally overwrites all existing ones."
)
@click.option(
    "-r",
    "--regenerate",
    is_flag=True,
    default=False,
    help="Whether to do a full re-generation, including of stamps that already have a context image."
)
@click.option(
    "-t",
    "--test",
    is_flag=True,
    default=False,
    help="Whether to only re-generate a single context stamp for test purposes."
)
@click.option(
    "-s",
    "--substitute",
    nargs=1,
    type=click.Path(dir_okay=True, exists=True),
    default=None,
    help="An optional path to a 'substitute image' to use instead of the real stamps."
)
@click.pass_context
def create_context(
        ctx: dict, regenerate: bool = False, test: bool = False, substitute: str = False
) -> None:
    """
    Create 'context' stamps for stamps.

    Generates context stamps for those that don't have any by default,
    or optionally overwrites all existing ones.

    Parameters
    ----------
    regenerate: bool
        Whether or not to re-generate *all* context stamps, including ones previously made.
        Defaults to fale.
    test: bool
        Whether or not to only re-generate a single context stamp, and provide the name.
        This is in order to test modifiations to the context generation code.
    substitute: str
        An optional substitute image to use instead of the real stamps.
        Used for if you're testing the code in an environment around people who shouldn't see medical images.
    """

    with Session(
        engine := voidorchestra.db.connect_to_database_engine(config["PATHS"]["database"])
    ) as session:

        if substitute and not Path(substitute).exists():
            raise FileNotFoundError("Substitute image does not exist")

        if regenerate or test:
            click.echo("Re-generating context stamps")
            stamps: List[Stamp] = session.query(Stamp).all()
            if stamps:
                generate_stamps_context(
                    session=session,
                    stamps=[stamps[0]] if test else stamps,
                    substitute=substitute
                )
            else:
                click.echo("No stamps in database!")

        else:
            stamps: List[Stamp] = session.query(Stamp).filter_by(filepath=None).all()
            if stamps:
                generate_stamps_context(
                    session=session,
                    stamps=stamps,
                    substitute=substitute
                )
            else:
                click.echo("No un-processed stamps in database!")

        if test and stamps:
            click.echo(f"Test context stamp:\n {Path(config['PATHS']['stamps_context'])/stamps[0].filepath}")

    if ctx.obj["VERBOSE"] or ctx.obj["DEBUG"]:
        click.echo(f"Generated new context stamps from database")

