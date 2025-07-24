#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains sub-commands for `voidorchestra upload`.

The commands should be used to upload new things, such as subjects or subject
sets, to the Zooniverse project.
"""
import click
from click import Context
from panoptes_client import Project as PanoptesProject, Workflow as PanoptesWorkflow
from sqlalchemy.orm import Session

from voidorchestra import config, config_paths
from voidorchestra.db import SonificationProfile, connect_to_database_engine
from voidorchestra.zooniverse.subjects import upload_sonifications_to_zooniverse
from voidorchestra.zooniverse.zooniverse import connect_to_zooniverse, open_zooniverse_project


@click.group()
def upload():
    """
    Upload new things and changes to Zooniverse
    """


@upload.command(name="sonifications")
@click.pass_context
@click.option(
    "--zooniverse_project_id",
    nargs=1,
    type=int,
    default=config["ZOONIVERSE"].getint("project_id"),
    show_default=True,
    help="The Zooniverse ID for a project",
)
def upload_new_sonifications(
    ctx: Context,
    zooniverse_project_id: int,
) -> None:
    """
    Add and upload stamps to MoleMarshal and Zooniverse

    This sub-command can be used to upload new sonifications to a subject set or to
    create a new subject set.

    The default behaviour will upload sonifications to a subject set based on their sonification profile.
    """
    connect_to_zooniverse()
    upload_sonifications_to_zooniverse(
        panoptes_project_id=zooniverse_project_id,
        commit_frequency=ctx.obj["COMMIT_FREQUENCY"],
    )
