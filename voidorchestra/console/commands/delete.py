#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains sub-commands for `molegazer remove`.

These are (mostly) development commands designed to remove the DB
"""

from logging import Logger
from pathlib import Path
from typing import List

import click
from click import Context
from sqlalchemy.orm import Session

import voidorchestra.log
from voidorchestra import config_paths
from voidorchestra.db import (
    LightcurveCollection,
    QPOModel,
    Sonification,
    SonificationMethodSoundfont,
    SonificationProfile,
    connect_to_database_engine,
)

logger: Logger = voidorchestra.log.get_logger(__name__.replace(".", "-"))


@click.group()
def delete():
    """
    Remove files of a given type.
    """


@delete.command(name="database", help="Deletes the database.")
@click.pass_context
def delete_database(
    ctx: Context,  # noqa: D417
) -> None:
    """
    Deletes the databasefilter(
    """
    database_path: Path = Path(config_paths["database"])

    if database_path.exists():
        database_path.unlink()

        click.echo(f"Deleted database at {database_path}")
    else:
        click.echo(f"No database to delete at {database_path}")


@delete.command(name="sonifications", help="Clears generated sonifications from the database, and deletes the files.")
@click.pass_context
@click.option(
    "-h",
    "--hard",
    is_flag=True,
    default=False,
    help="Whether to fully clear the output directory, even if there is no DB",
)
def delete_sonifications(
    ctx: Context,  # noqa: D417
    hard: bool = False,
) -> None:
    """
    Clear image files that have been uploaded.

    Clears uploaded sonifications from the database, and deletes the files.

    Parameters
    ----------
    hard: bool
        Whether to process images that are not in the database (or if there is no database)
    """
    directory_output: Path = Path(config_paths["output"])

    try:
        with Session(
            engine := connect_to_database_engine(config_paths["database"]),
            info={"url": engine.url},
        ) as session:
            sonifications: List[Sonification] = session.query(Sonification).all()  # This bit is only here to type-hint for the IDE
            num_sonifications_deleted: int = 0

            for sonification in sonifications:
                if sonification.path_audio and (path_audio := directory_output / sonification.path_audio).is_file():
                    path_audio.unlink()
                if sonification.path_video and (path_video := directory_output / sonification.path_video).is_file():
                    path_video.unlink()
                if sonification.path_image and (path_image := directory_output / sonification.path_image).is_file():
                    path_image.unlink()

                num_sonifications_deleted += 1
                logger.debug(f"Deleting sonification {sonification}\n")
                session.delete(sonification)
                session.commit()

        if ctx.obj["VERBOSE"] or ctx.obj["DEBUG"]:
            click.echo(f"Deleted {num_sonifications_deleted} sonifications from database")

    except Exception as e:
        click.echo(f"Could not connect to database: {e}")

    if hard:
        num_sonifications_deleted: int = 0

        for path_sonification in directory_output.rglob("*.png"):
            path_sonification.unlink()

        for path_sonification in directory_output.rglob("*.mp*"):
            path_sonification.unlink()

            num_sonifications_deleted += 1

        click.echo(f"Deleted {num_sonifications_deleted} sonification files not in database")


@delete.command(name="soundfonts", help="Clears added soundfonts from the database.")
@click.pass_context
def delete_soundfonts(
    ctx: Context,  # noqa: D417
) -> None:
    """
    Remove soundfonts that have been imported from the database.
    """
    try:
        with Session(
            engine := connect_to_database_engine(config_paths["database"]),
            info={"url": engine.url},
        ) as session:
            soundfonts: List[SonificationMethodSoundfont] = session.query(SonificationMethodSoundfont).all()
            for soundfont in soundfonts:
                session.delete(soundfont)
                session.commit()

            if ctx.obj["VERBOSE"] or ctx.obj["DEBUG"]:
                click.echo(f"Deleted {len(soundfonts)} soundfonts from database")

    except Exception as e:
        click.echo(f"Could not connect to database: {e}")


@delete.command(name="profiles", help="Clears added sonification profiles from the database.")
@click.pass_context
def delete_sonification_profiles(
    ctx: Context,  # noqa: D417
) -> None:
    """
    Remove imported sonification profiles from the database.
    """
    try:
        with Session(
            engine := connect_to_database_engine(config_paths["database"]),
            info={"url": engine.url},
        ) as session:
            sonification_profiles: List[SonificationProfile] = session.query(SonificationProfile).all()
            for sonification_profile in sonification_profiles:
                session.delete(sonification_profile)
                session.commit()

            if ctx.obj["VERBOSE"] or ctx.obj["DEBUG"]:
                click.echo(f"Deleted {len(sonification_profiles)} sonification profiles from database")

    except Exception as e:
        click.echo(f"Could not connect to database: {e}")


@delete.command(name="collection", help="Clears sonifications and lightcurves associated with a collection from the database.")
@click.pass_context
@click.argument(
    "lightcurve_collection",
)
def delete_lightcurve_collection(
    ctx: Context,  # noqa: D417
    lightcurve_collection: str,
) -> None:
    """
    Remove imported sonification profiles from the database.
    """
    lightcurves_deleted: int = 0
    sonifications_deleted: int = 0

    try:
        with Session(
            engine := connect_to_database_engine(config_paths["database"]),
            info={"url": engine.url},
        ) as session:
            try:
                lightcurve_collection: LightcurveCollection = (
                    session.query(LightcurveCollection).filter(LightcurveCollection.id == int(lightcurve_collection)).all()[0]
                )
            except Exception:
                try:
                    lightcurve_collection = session.query(LightcurveCollection).filter(LightcurveCollection.name == lightcurve_collection).all()[0]
                except Exception:
                    click.echo(f"Could not find collection '{lightcurve_collection}' in database")
                    return

            for lightcurve in lightcurve_collection.lightcurves:
                for sonification in lightcurve.sonifications:
                    session.delete(sonification)
                    sonifications_deleted += 1

                    if sonification.path_audio and (path_audio := Path(sonification.path_audio)).is_file():
                        path_audio.unlink()
                    if sonification.path_video and (path_video := Path(sonification.path_video)).is_file():
                        path_video.unlink()
                    if sonification.path_image and (path_image := Path(sonification.path_image)).is_file():
                        path_image.unlink()

                lightcurves_deleted += 1
                session.delete(lightcurve)

            session.delete(lightcurve_collection)
            session.commit()

            click.echo(
                f"Deleted lightcurve collection {lightcurve_collection}, including {lightcurves_deleted} lightcurves and {sonifications_deleted} sonifications from database"
            )

    except Exception as e:
        click.echo(f"Could not connect to database: {e}")


@delete.command(name="models", help="Clears unused QPO models from the database.")
@click.pass_context
def delete_qpo_models(
    ctx: Context,  # noqa: D417
) -> None:
    """
    Remove unused QPO models from the database.

    Any QPO model that isn't being used by a lightcurve is deleted, including sub-components of composite models.
    """
    qpo_models_deleted: int = 0
    qpo_model_components_deleted: int = 0
    qpo_models_path: Path = config_paths["output"] / "qpo_models"

    try:
        with Session(
            engine := connect_to_database_engine(config_paths["database"]),
            info={"url": engine.url},
        ) as session:
            qpo_models: List[QPOModel] = session.query(QPOModel).filter(QPOModel.qpo_model_parent_id == None).all()
            click.echo(f"Found {len(qpo_models)} top-level QPO models in database")

            for qpo_model in qpo_models:
                if not len(qpo_model.lightcurves):
                    psd_path: Path = qpo_models_path / f"qpo_model-{qpo_model.id}.psd.png"
                    if psd_path.exists() and psd_path.is_file():
                        psd_path.unlink()

                    for qpo_model_child in qpo_model.qpo_model_children:
                        session.delete(qpo_model_child)
                        qpo_model_components_deleted += 1

                    qpo_models_deleted += 1
                    session.delete(qpo_model)

            session.commit()
            click.echo(f"Deleted {qpo_models_deleted} unused QPO models, {qpo_model_components_deleted} components.")

    except Exception as e:
        click.echo(f"Could not connect to database: {e}")
