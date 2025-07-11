#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""This module contains sub-commands for `molemarshal check`.

The commands should check properties or statistics for various parts of the
MoleMarshal package or for the Zooniverse project and its components.
"""

import click
from panoptes_client import Workflow
from panoptes_client import Project
from panoptes_client.panoptes import PanoptesAPIException


import voidorchestra
import voidorchestra.zooniverse.zooniverse


@click.group()
def check():
    """
    Check info about Void Orchestra and Zooniverse
    """


@check.command(name="version")
def print_version() -> None:
    """Print the Void Orchestra package version"""
    click.echo(f"{voidorchestra.__version__}")


@check.command(name="workflow")
@click.option(
    "-id",
    "--workflow_id",
    nargs=1,
    type=int,
    default=voidorchestra.config["ZOONIVERSE"]["workflow_id"],
    show_default=True,
    help="The ID of the workflow to check statistics for",
)
def workflow_stats(workflow_id: str) -> None:
    """
    Print workflow statistics

    :param workflow_id: The ID of the workflow to check statistics for.
    """
    voidorchestra.zooniverse.zooniverse.connect_to_zooniverse()

    try:
        workflow = Workflow.find(workflow_id)
    except PanoptesAPIException:
        click.echo(f"Unable to open workflow with ID {workflow_id}")
        return

    click.echo(f"ID: {workflow.id}")
    click.echo(f"Workflow: {workflow.display_name}")
    click.echo(f"Workflow version: {workflow.raw['version']}")
    click.echo(f"Subject count: {workflow.raw['subjects_count']}")
    click.echo(f"Classifications count: {workflow.raw['classifications_count']}")
    click.echo(f"Retired count: {workflow.raw['retired_set_member_subjects_count']}")
    click.echo(f"Subject sets: {', '.join(workflow.raw['links']['subject_sets'])}")
    click.echo(f"Completeness: {workflow.raw['completeness'] * 100:.0f}%")
    click.echo(f"Configuration: {workflow.configuration}")


@check.command(name="project")
@click.option(
    "-id",
    "--project_id",
    nargs=1,
    type=int,
    default=voidorchestra.config["ZOONIVERSE"]["project_id"],
    show_default=True,
    help="The ID of the project to check statistics for",
)
def project_stats(project_id: str) -> None:
    """
    Print project information

    :param project_id: The ID of the project to check statistics for.
    """
    voidorchestra.zooniverse.zooniverse.connect_to_zooniverse()
    if not project_id:
        project_id = voidorchestra.config['ZOONIVERSE']['project_id']

    try:
        project = Project.find(project_id)
    except PanoptesAPIException:
        click.echo(f"Unable to open project with ID {project_id}")

    click.echo(f"ID: {project.id}")
    click.echo(f"Project: {project.display_name}")
    click.echo(f"Workflows: {', '.join(project.raw['links']['active_workflows'])}")
    click.echo(f"Subject sets: {', '.join(project.raw['links']['subject_sets'])}")
    click.echo(f"Subject count: {project.raw['subjects_count']}")
    click.echo(f"Classification count: {project.raw['classifications_count']}")
    click.echo(f"Completeness: {project.raw['completeness']}")
    click.echo(f"Configuration: {project.raw['configuration']}")
