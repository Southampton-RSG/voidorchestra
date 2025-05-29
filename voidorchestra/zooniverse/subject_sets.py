#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Panoptes client https://panoptes-python-client.readthedocs.io/en/latest/

"""
The subject sets module contains functions which are used to manage subject
sets on Zooniverse. It does not contain any functionality for the active
learning "priority" subject sets.
"""

from __future__ import annotations

from panoptes_client import Project
from panoptes_client import SubjectSet


# Private functions ------------------------------------------------------------


def __create_new_subject_set(project: Project, subject_set_name: str) -> SubjectSet:
    """Create a new subject set on Zooniverse.

    Creates a new SubjectSet with the name :code:`subject_set_name` and is
    linked to the project :code:`project`.

    Parameters
    ----------
    project: Project
        The project to check.
    subject_set_name: str
        The name of the subject set to check against.

    Returns
    -------
    subject_set: SubjectSet
        The new subject set, with the given name and linked to the given
        project.
    """
    subject_set = SubjectSet()
    subject_set.links.project = project
    subject_set.display_name = subject_set_name
    subject_set.save()

    return subject_set


# Public functions -------------------------------------------------------------


def get_named_subject_set_in_project(project: Project, proposed_subject_set_name: str) -> SubjectSet:
    """Retrieve or create a named subject set in a project.

    The provided project will be checked to see if the named subject set exists
    or not. If it does not, then a new subject set with the given name is
    created. A new subject set will also be created if the project has no
    subject sets.

    Parameters
    ----------
    project: Project
        The project to check.
    proposed_subject_set_name: str
        The name of the subject set to check against.

    Returns
    -------
    subject_set: SubjectSet
        The subject set of the given name. This is either a new subject set
        or one which already existed and was linked to the project.
    """
    project_subject_sets = list(project.links.subject_sets)
    # no subject sets exist, start from scratch
    if len(project_subject_sets) == 0:
        return __create_new_subject_set(project, proposed_subject_set_name)

    project_subject_set_names = [subject_set.display_name for subject_set in project_subject_sets]
    # new subject set for project, start from scratch
    if proposed_subject_set_name not in project_subject_set_names:
        return __create_new_subject_set(project, proposed_subject_set_name)

    # since the subject set must exist, find the index in the name list and
    # return the SubjectSet object
    idx = project_subject_set_names.index(proposed_subject_set_name)
    return project.links.subject_sets[idx]
