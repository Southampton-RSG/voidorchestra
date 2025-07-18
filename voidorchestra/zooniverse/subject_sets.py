#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Panoptes client https://panoptes-python-client.readthedocs.io/en/latest/
"""
The subject sets module contains functions which are used to manage subject
sets on Zooniverse. It does not contain any functionality for the active
learning "priority" subject sets.
"""
from typing import List

from panoptes_client import Project as PanoptesProject, SubjectSet as PanoptesSubjectSet


# Private functions ------------------------------------------------------------
def __create_new_panoptes_subject_set(
        panoptes_project: PanoptesProject,
        subject_set_name: str
) -> PanoptesSubjectSet:
    """
    Create a new subject set on Zooniverse.

    Creates a new SubjectSet with the name :code:`subject_set_name` and is
    linked to the project :code:`project`.

    Parameters
    ----------
    panoptes_project: PanoptesProject
        The project to check.
    subject_set_name: str
        The name of the subject set to check against.

    Returns
    -------
    panoptes_subject_set: SubjectSet
        The new subject set, with the given name and linked to the given
        project.
    """
    panoptes_subject_set = PanoptesSubjectSet()
    panoptes_subject_set.links.project = panoptes_project
    panoptes_subject_set.display_name = subject_set_name
    panoptes_subject_set.save()

    return panoptes_subject_set


# Public functions -------------------------------------------------------------
def get_named_panoptes_subject_set_in_panoptes_project(
        panoptes_project: PanoptesProject,
        proposed_subject_set_name: str
) -> PanoptesSubjectSet:
    """
    Retrieve or create a named subject set in a project.

    The provided project will be checked to see if the named subject set exists
    or not. If it does not, then a new subject set with the given name is
    created. A new subject set will also be created if the project has no
    subject sets.

    Parameters
    ----------
    panoptes_project: Project
        The project to check.
    proposed_subject_set_name: str
        The name of the subject set to check against.

    Returns
    -------
    panoptes_subject_set: PanoptesSubjectSet
        The subject set of the given name. This is either a new subject set
        or one which already existed and was linked to the project.
    """
    panoptes_project_subject_sets: List[PanoptesSubjectSet] = list(panoptes_project.links.subject_sets)
    # no subject sets exist, start from scratch
    if len(panoptes_project_subject_sets) == 0:
        return __create_new_panoptes_subject_set(panoptes_project, proposed_subject_set_name)

    project_subject_set_names = [panoptes_subject_set.display_name for panoptes_subject_set in panoptes_project_subject_sets]
    # new subject set for project, start from scratch
    if proposed_subject_set_name not in project_subject_set_names:
        return __create_new_panoptes_subject_set(panoptes_project, proposed_subject_set_name)

    # since the subject set must exist, find the index in the name list and
    # return the PanoptesSubjectSet object
    idx: int = project_subject_set_names.index(proposed_subject_set_name)
    return panoptes_project.links.subject_sets[idx]
