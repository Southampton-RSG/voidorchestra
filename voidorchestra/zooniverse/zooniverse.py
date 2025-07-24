#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Panoptes client https://panoptes-python-client.readthedocs.io/en/latest/
"""
The Zooniverse module contains functions to connect to Zooniverse and modify
the very top level objects, such as projects.
"""
from logging import Logger

from panoptes_client import Panoptes, Project as PanoptesProject
from panoptes_client.panoptes import PanoptesAPIException

from voidorchestra import config
from voidorchestra.log import get_logger

logger: Logger = get_logger(__name__.replace(".", "-"))


def connect_to_zooniverse() -> None:
    """
    Connect to Zooniverse using the Panoptes client.

    Credentials are taken from the voidorchestra.ini configuration file.

    If user credentials are incorrect, a PanoptesAPIException is raised because
    the panoptes client cannot connect to the Zooniverse servers. This exception
    is caught and a more descriptive error is printed to the logger and the
    code will be exited.
    """
    zooniverse_account: str = config["CREDENTIALS"]["username"]
    zooniverse_password: str = config["CREDENTIALS"]["password"]

    if not zooniverse_account or not zooniverse_password:
        raise SyntaxError("Either the user or password are empty in configuration file.")

    try:
        Panoptes.connect(username=zooniverse_account, password=zooniverse_password)
    except PanoptesAPIException as exception:
        raise ValueError("Invalid Zooniverse username and password combination.") from exception

    logger.info(f"Connected to Panoptes with account: {zooniverse_account}.")


def open_zooniverse_project(
        panoptes_project_id: str | int | None = None,
) -> PanoptesProject:
    """
    Retrieve a Zooniverse project with the given ID.

    If the project cannot be found, a PanoptesAPIException will be raised. Since
    this is not a very descriptive error, an error will be printed to the logger
    and the program will exit.

    Parameters
    ----------
    panoptes_project_id: str | int | None
        The ID for the Zooniverse project.
        Defaults to the value from the project config files.

    Returns
    -------
    panoptes_project: PanoptesProject
        The project requested.
    """
    if not panoptes_project_id:
        panoptes_project_id = config["ZOONIVERSE"]["project_id"]

    try:
        panoptes_project: PanoptesProject = PanoptesProject.find(panoptes_project_id)
    except PanoptesAPIException as exception:
        raise ValueError(f"Unable to find a project with ID {panoptes_project_id}") from exception

    logger.debug("Opened project %s", panoptes_project.title)

    return panoptes_project
