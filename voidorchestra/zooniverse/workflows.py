#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Panoptes client https://panoptes-python-client.readthedocs.io/en/latest/

"""
This module handles assigning workflows to subject sets, as well as getting
and modifying workflows.
"""

from __future__ import annotations

import logging

from panoptes_client import SubjectSet, Workflow
from panoptes_client.panoptes import PanoptesAPIException

import voidorchestra.log

logger: logging.Logger = voidorchestra.log.get_logger(__name__.replace(".", "-"))


def get_workflow(workflow_id: str | int) -> Workflow:
    """
    Retrieve a workflow for a given workflow ID.

    This function relies in `panoptes_client.Workflow.find()` to find a workflow
    of the given ID. If no workflow can be found, then a PanoptesAPIException
    is raised.

    Parameters
    ----------
    workflow_id: str | int
        The ID of the workflow.

    Returns
    -------
    workflow: panoptes_client.Workflow
        The workflow associated with the ID.
    """
    return Workflow.find(workflow_id)


def assign_workflow_to_subject_set(workflow: Workflow, subject_set: SubjectSet) -> None:
    """
    Assign a given workflow to a subject set.

    This process is wrapped in this function as if you try to assign an already
    assigned workflow to a subject set, a PanoptesAPIException is raised. This
    wrapper stops Void Orchestra from crashing by sending debug output instead of
    allowing the exception to be raised.

    Parameters
    ----------
    workflow: panoptes_client.Workflow
        The workflow object to add a subject set to.
    subject_set: panoptes_client.SubjectSet
        The subject set to add to the workflow.
    """
    workflow.reload()
    try:
        workflow.add_subject_sets([subject_set])
        workflow.save()
    except PanoptesAPIException:
        logger.debug("Subject set %d is already linked to workflow %d", subject_set.id, workflow.id)
    logger.debug("Subject set %s added to workflow %s", subject_set.id, workflow.id)
