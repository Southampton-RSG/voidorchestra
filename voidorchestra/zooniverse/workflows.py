#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Panoptes client https://panoptes-python-client.readthedocs.io/en/latest/
"""
This module handles assigning workflows to subject sets, as well as getting
and modifying workflows.
"""

from logging import Logger

from panoptes_client import SubjectSet as PanoptesSubjectSet, Workflow as PanoptesWorkflow
from panoptes_client.panoptes import PanoptesAPIException

from voidorchestra.log import get_logger

logger: Logger = get_logger(__name__.replace(".", "-"))


def get_panoptes_workflow(panoptes_workflow_id: str | int) -> PanoptesWorkflow:
    """
    Retrieve a workflow for a given workflow ID.

    This function relies in `panoptes_client.Workflow.find()` to find a workflow
    of the given ID. If no workflow can be found, then a PanoptesAPIException
    is raised.

    Parameters
    ----------
    panoptes_workflow_id: str | int
        The ID of the workflow.

    Returns
    -------
    panoptes_workflow: PanoptesWorkflow
        The workflow associated with the ID.
    """
    return PanoptesWorkflow.find(panoptes_workflow_id)


def assign_panoptes_workflow_to_panoptes_subject_set(
    panoptes_workflow: PanoptesWorkflow, panoptes_subject_set: PanoptesSubjectSet
) -> None:
    """
    Assign a given workflow to a subject set.

    This process is wrapped in this function as if you try to assign an already
    assigned workflow to a subject set, a PanoptesAPIException is raised. This
    wrapper stops Void Orchestra from crashing by sending debug output instead of
    allowing the exception to be raised.

    Parameters
    ----------
    panoptes_workflow: panoptes_client.Workflow
        The workflow object to add a subject set to.
    panoptes_subject_set: panoptes_client.SubjectSet
        The subject set to add to the workflow.
    """
    panoptes_workflow.reload()
    try:
        panoptes_workflow.add_subject_sets([panoptes_subject_set])
        panoptes_workflow.save()
    except PanoptesAPIException:
        logger.debug(
            f"Subject set {panoptes_subject_set.id} is already linked to workflow {panoptes_workflow.id}",
        )

    logger.debug(
        f"Subject set {panoptes_subject_set.id} added to workflow {panoptes_workflow.id}",
    )
