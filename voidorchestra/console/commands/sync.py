#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains sub-commands for `voidorchestra sync`.

The commands should be used to sync the Void Orchestra database with Zooniverse.
"""
import click
from click import Choice, Context
from panoptes_client import Subject, SubjectSet
from sqlalchemy.orm import Session

from voidorchestra import config
from voidorchestra.db import connect_to_database_engine
from voidorchestra.zooniverse.classifications import update_classification_database
from voidorchestra.zooniverse.sync import sync_local_subject_set_database_with_zooniverse, sync_subject_database_with_zooniverse
from voidorchestra.zooniverse.zooniverse import connect_to_zooniverse


@click.group()
def sync():
    """
    Sync Void Orchestra with Zooniverse
    """


@sync.command(name="subjects")
@click.pass_context
@click.argument(
    "source", nargs=1,
    type=Choice(
        ["project", "subject_set", "workflow"],
        case_sensitive=False
    ),
)
@click.option(
    "-id",
    "--source_id",
    nargs=1,
    type=int,
    default=None,
    help="An optional specified ID for the source if not using the default",
)
def update_subject_table(
        ctx: Context,  # noqa: undocumented-param
        source: str,
        source_id: int
) -> None:
    """
    Sync the subject database with Zooniverse

    Using this sub-command, the subject database can be updated by providing
    the ID to the Zooniverse project. Each subject which is attached to the
    project will be added/updated in the MoleMarshal database.

    \b
    Arguments:

        \b
        source     The source to get subjects from {project|subject_set|workflow}
    """
    connect_to_zooniverse()

    if source == "project":
        subjects_to_add = Subject.where(
            project_id=source_id if source_id else (source_id := int(config["ZOONIVERSE"]["project_id"]))
        )
    elif source == "subject_set":
        subjects_to_add = Subject.where(
            subject_set_id=source_id if source_id else (source_id := config["ZOONIVERSE"]["subject_set_id"])
        )
    elif source == "workflow":
        subjects_to_add = Subject.where(
            workflow_id=source_id if source_id else (source_id := config["ZOONIVERSE"]["workflow_id"])
        )
    else:
        raise ValueError(f"{source} is an unknown option")

    if subjects_to_add.meta["count"] == 0:
        click.echo(f"No subjects found in {source} with ID {source_id}")
        return

    with Session(
            engine := connect_to_database_engine(config["PATHS"]["database"]),
            info={"url": engine.url}
    ) as session:
        sync_subject_database_with_zooniverse(
            session,
            subjects_to_add,
            subjects_to_add.meta["count"],
            ctx.obj["COMMIT_FREQUENCY"],
        )


@sync.command(name="subject-sets")
@click.pass_context
@click.argument("source", nargs=1, type=click.Choice(["project", "workflow"]))
@click.option(
    "-id",
    "--source_id",
    nargs=1,
    type=int,
    default=None,
    help="An optional specified ID for the source if not using the default",
)
def update_subject_set_table(
        ctx: Context,   # noqa: undocumented-param
        source: str,
        source_id: int
) -> None:
    """
    Sync the subject set database with Zooniverse

    Using this sub-command, the subject set database can be updated by providing
    the ID to a Zooniverse project or workflow. Each subject set that is
    attached to the provided source will then be added/updated in the
    MoleMarshal database.

    \b
    Arguments:

        \b
        source     The source to get subjects from {project|workflow}
        source_id  The Zooniverse ID of the source
    """
    connect_to_zooniverse()

    if source == "project":
        subject_sets_to_add = SubjectSet.where(
            project_id=source_id if source_id else (source_id := config["ZOONIVERSE"]["project_id"])
        )
    elif source == "workflow":
        subject_sets_to_add = SubjectSet.where(
            workflow_id=source_id if source_id else (source_id := config["ZOONIVERSE"]["workflow_id"])
        )
    else:
        raise ValueError(f"{source} is an unknown option. Allowed: project, workflow")

    num_subject_sets = subject_sets_to_add.meta["count"]

    if num_subject_sets == 0:
        click.echo(f"No subjects sets found in {source} with ID {source_id}")
        return

    with Session(
        engine := connect_to_database_engine(config["PATHS"]["database"]),
        info={"url": engine.url},
    ) as session:
        sync_local_subject_set_database_with_zooniverse(
            session, subject_sets_to_add,
            subject_sets_to_add.meta["count"], ctx.obj["COMMIT_FREQUENCY"]
        )


@sync.command(name="classifications")
@click.pass_context
@click.option(
    "-id",
    "--zooniverse_workflow_id",
    nargs=1,
    type=int,
    help="The ID of the Zooniverse workflow, if not the default",
)
def update_classification_table(
        ctx: Context,
        zooniverse_workflow_id: int
) -> None:
    """
    Add classifications to the MoleMarshal database

    Using this sub-command, the current classifications from a given Zooniverse
    workflow will be downloaded. Note that this sub-command assumes that Caesar
    extractors and reducers are in used to generate consensus classifications.
    """
    connect_to_zooniverse()
    update_classification_database(
        zooniverse_workflow_id,
        ctx.obj["COMMIT_FREQUENCY"],
    )
