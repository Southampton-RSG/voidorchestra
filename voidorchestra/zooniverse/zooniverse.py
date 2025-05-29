#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Panoptes client https://panoptes-python-client.readthedocs.io/en/latest/

"""
The Zooniverse module contains functions to connect to Zooniverse and modify
the very top level objects, such as projects.
"""
from __future__ import annotations
from logging import Logger

from panoptes_client import Panoptes
from panoptes_client import Project
from panoptes_client.panoptes import PanoptesAPIException

import voidorchestra.log
from voidorchestra import config


logger: Logger = voidorchestra.log.get_logger(__name__.replace(".", "-"))


def connect_to_zooniverse() -> None:
    """
    Connect to Zooniverse using the Panoptes client.

    Credentials are taken from the molemarshal.ini configuration file.

    If user credentials are incorrect, a PanoptesAPIException is raised because
    the panoptes client cannot connect to the Zooniverse servers. This exception
    is caught and a more descriptive error is printed to the logger and the
    code will be exited.
    """
    zooniverse_account: str = config["CREDENTIALS"]["username"]
    zooniverse_password: str = config["CREDENTIALS"]["password"]

    if not zooniverse_account or not zooniverse_password:
        raise SyntaxError("Either the user or password are empty in configuration file")

    try:
        Panoptes.connect(username=zooniverse_account, password=zooniverse_password)
    except PanoptesAPIException as exception:
        raise ValueError("Invalid Zooniverse username and password combination.") from exception

    logger.info("Connected to Panoptes with account %s", zooniverse_account)


def open_zooniverse_project(project_id: str | int) -> Project:
    """
    Retrieve a Zooniverse project with the given ID.

    If the project cannot be found, a PanoptesAPIException will be raised. Since
    this is not a very descriptive error, an error will be printed to the logger
    and the program will exit.

    Parameters
    ----------
    project_id: str | str
        The ID for the Zooniverse project.

    Returns
    -------
    project: panoptes_client.Project
        The project requested.
    """
    try:
        project = Project.find(project_id)
    except PanoptesAPIException as exception:
        raise ValueError(f"Unable to find a project with ID {project_id}") from exception

    logger.debug("Opened project %s", project.title)

    return project
