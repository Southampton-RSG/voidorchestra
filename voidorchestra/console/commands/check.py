#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains sub-commands for `voidorchestra check`.

The commands should check properties or statistics for various parts of the
Voidorchestra package or for the Zooniverse project and its components.
"""

from typing import List

import click
from click import Context
from panoptes_client import Project as PanoptesProject, Workflow as PanoptesWorkflow
from panoptes_client.panoptes import PanoptesAPIException
from sqlalchemy.orm import Session

import voidorchestra
from voidorchestra import config
from voidorchestra.db import LightcurveCollection, connect_to_database_engine
from voidorchestra.zooniverse.zooniverse import connect_to_zooniverse


@click.group()
def check():
    """
    Check info about Void Orchestra and Zooniverse
    """


@check.command(name="version")
def print_version() -> None:
    """
    Print the Void Orchestra package version
    """
    click.echo(f"{voidorchestra.__version__}")


@check.command(name="workflow")
@click.option(
    "-id",
    "--panoptes_workflow_id",
    nargs=1,
    type=int,
    default=config["ZOONIVERSE"].getint("workflow_id"),
    show_default=True,
    help="The ID of the workflow to check statistics for",
)
def workflow_stats(panoptes_workflow_id: int) -> None:
    """
    Print workflow statistics

    Parameters
    ----------
    panoptes_workflow_id: int
        The ID of the workflow to check statistics for.
    """
    connect_to_zooniverse()

    try:
        panoptes_workflow: PanoptesWorkflow = PanoptesWorkflow.find(panoptes_workflow_id)
        click.echo(f"ID: {panoptes_workflow.id}")
        click.echo(f"Workflow: {panoptes_workflow.display_name}")
        click.echo(f"Workflow version: {panoptes_workflow.raw['version']}")
        click.echo(f"Subject count: {panoptes_workflow.raw['subjects_count']}")
        click.echo(f"Classifications count: {panoptes_workflow.raw['classifications_count']}")
        click.echo(f"Retired count: {panoptes_workflow.raw['retired_set_member_subjects_count']}")
        click.echo(f"Subject sets: {', '.join(panoptes_workflow.raw['links']['subject_sets'])}")
        click.echo(f"Completeness: {panoptes_workflow.raw['completeness'] * 100:.0f}%")
        click.echo(f"Configuration: {panoptes_workflow.configuration}")

    except PanoptesAPIException:
        click.echo(f"Unable to open workflow with ID {panoptes_workflow_id}")
        return


@check.command(name="project")
@click.option(
    "-id",
    "--panoptes_project_id",
    nargs=1,
    type=int,
    default=config["ZOONIVERSE"]["project_id"],
    show_default=True,
    help="The ID of the project to check statistics for",
)
def project_stats(panoptes_project_id: int) -> None:
    """
    Print project information

    Parameters
    ----------
    panoptes_project_id: int
        The ID of the project to check statistics for.
    """
    connect_to_zooniverse()
    if not panoptes_project_id:
        panoptes_project_id: int = config["ZOONIVERSE"].getint("project_id")

    try:
        panoptes_project: PanoptesProject = PanoptesProject.find(panoptes_project_id)
        click.echo(f"ID: {panoptes_project.id}")
        click.echo(f"Project: {panoptes_project.display_name}")
        click.echo(f"Workflows: {', '.join(panoptes_project.raw['links']['active_workflows'])}")
        click.echo(f"Subject sets: {', '.join(panoptes_project.raw['links']['subject_sets'])}")
        click.echo(f"Subject count: {panoptes_project.raw['subjects_count']}")
        click.echo(f"Classification count: {panoptes_project.raw['classifications_count']}")
        click.echo(f"Completeness: {panoptes_project.raw['completeness']}")
        click.echo(f"Configuration: {panoptes_project.raw['configuration']}")

    except PanoptesAPIException:
        click.echo(f"Unable to open project with ID {panoptes_project_id}")


@check.command(name="collections")
@click.pass_context
def check_collections(
    ctx: Context,  # noqa: D417
) -> None:
    """
    Print project information

    Parameters
    ----------

    """
    with Session(engine := connect_to_database_engine(config["PATHS"]["database"]), info={"url": engine.url}) as session:
        lightcurve_collections: List[LightcurveCollection] = session.query(LightcurveCollection).all()
        for lightcurve_collection in lightcurve_collections:
            click.echo(f"* {lightcurve_collection.id} - {lightcurve_collection.name}: {len(lightcurve_collection.lightcurves)}")
