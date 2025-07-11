#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This module contains sub-commands for `voidorchestra upload`.

The commands should be used to upload new things, such as subjects or subject
sets, to the Zooniverse project.
"""

import click

import voidorchestra
import voidorchestra.zooniverse.subjects
import voidorchestra.zooniverse.zooniverse


@click.group()
def upload():
    """
    Upload new things and changes to Zooniverse
    """


@upload.command(name="subjects")
@click.pass_context
@click.option(
    "-project",
    nargs=1,
    type=int,
    default=voidorchestra.config["ZOONIVERSE"]["project_id"],
    show_default=True,
    help="The Zooniverse ID for a project",
)
@click.option(
    "-workflow",
    nargs=1,
    type=int,
    default=voidorchestra.config["ZOONIVERSE"]["workflow_id"],
    show_default=True,
    help="The Zooniverse ID of a workflow to link the subject set to",
)
@click.option(
    "-subject_set",
    nargs=1,
    type=int,
    default=voidorchestra.config["ZOONIVERSE"]["subject_set_id"],
    show_default=True,
    help="The Zooniverse ID for the subject set to upload to",
)
@click.option(
    "-name",
    "--subject_set_name",
    type=str,
    default=None,
    help="The name of the subject set upload to"
)
def upload_new_sonifications(
    ctx: dict,
    project: int,
    workflow: int,
    subject_set: int,
    subject_set_name: str,
) -> None:
    """
    Add and upload stamps to MoleMarshal and Zooniverse

    This sub-command can be used to upload new stamps to a subject set or to
    create a new subject set.

    The default behaviour will upload stamps to the default "Mole Stamps"
    subject set. All the stamps in the stamp database will be added to the
    subject set.

    To create a new subject set, or to upload to a specific subject set by name,
    use the -name SUBJECT_SET_NAME option to either retrieve or create that
    subject set and upload to it.
    """
    voidorchestra.zooniverse.zooniverse.connect_to_zooniverse()
    voidorchestra.zooniverse.subjects.upload_to_subject_set(
        project,
        workflow,
        subject_set,
        subject_set_name,
        ctx.obj["COMMIT_FREQUENCY"],
    )
