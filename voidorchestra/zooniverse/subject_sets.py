#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Panoptes client https://panoptes-python-client.readthedocs.io/en/latest/
"""
The subject sets module contains functions which are used to manage subject
sets on Zooniverse. It does not contain any functionality for the active
learning "priority" subject sets.
"""

from panoptes_client import Project as PanoptesProject, SubjectSet as PanoptesSubjectSet


# Private functions ------------------------------------------------------------
def __create_new_panoptes_subject_set(
    panoptes_project: PanoptesProject,
    subject_set_name: str,
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
    panoptes_subject_set: PanoptesSubjectSet = PanoptesSubjectSet()
    panoptes_subject_set.display_name = subject_set_name
    panoptes_subject_set.links.project = panoptes_project
    panoptes_subject_set.save()

    panoptes_project.add_subject_sets(panoptes_subject_set)
    panoptes_project.save()

    return panoptes_subject_set


# Public functions -------------------------------------------------------------
def get_named_panoptes_subject_set_in_panoptes_project(
    panoptes_project: PanoptesProject,
    proposed_subject_set_name: str,
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
    panoptes_subject_set: PanoptesSubjectSet | None = None
    for panoptes_subject_set_iter in panoptes_project.links.subject_sets:
        if panoptes_subject_set_iter.display_name == proposed_subject_set_name:
            panoptes_subject_set = panoptes_subject_set_iter

    if not panoptes_subject_set:
        return __create_new_panoptes_subject_set(
            panoptes_project,
            proposed_subject_set_name,
        )
    else:
        return panoptes_subject_set
