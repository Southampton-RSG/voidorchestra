#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
This module contains operations to sync with the Zooniverse database.
"""
import logging
from logging import Logger
from typing import List, Tuple

from panoptes_client import Subject as PanoptesSubject, SubjectSet as PanoptesSubjectSet, Workflow as PanoptesWorkflow
from panoptes_client.panoptes import PanoptesAPIException
from sqlalchemy.orm import Query, Session
from tqdm import tqdm

from voidorchestra.db import Sonification, Subject as LocalSubject, SubjectSet as LocalSubjectSet, commit_database
from voidorchestra.log import get_logger

NO_SUBJECT_SET_ASSIGNED = None
NO_WORKFLOW_ASSIGNED = None

logger: Logger = get_logger(__name__.replace(".", "-"))


# Private functions ------------------------------------------------------------
def __check_panoptes_subject_valid(panoptes_subject: PanoptesSubject) -> Tuple[int, int, str]:
    """
    Check that a subject has "valid" setup.

    Check if a subject has a valid setup by checking for the ID of the subject
    set and workflow it is assigned to -- in theory both of these can be
    NULL or None. Additionally also get the stamp name. If this is None, then
    something has gone wrong with the subject.

    Parameters
    ----------
    panoptes_subject : Subject
        The subject to check.

    Returns
    -------
    Tuple[int, int, str]
        The subject set ID, the workflow ID and the name of the stamp.

    Raises
    ------
    ValueError
        Raised when a subject has been found to be in multiple subject sets.
    """
    # check subject set config is valid
    panoptes_subject_set_ids = panoptes_subject.raw["links"].get("subject_sets", [])
    if len(panoptes_subject_set_ids) == 0:
        panoptes_subject_set_id: int|None = NO_SUBJECT_SET_ASSIGNED
    elif len(panoptes_subject_set_ids) > 1:
        raise ValueError(f"Subject {panoptes_subject.id} is bad")
    else:
        panoptes_subject_set_id: int|None = int(panoptes_subject_set_ids[0])

    # check workflow config is valid
    if panoptes_subject_set_id is NO_SUBJECT_SET_ASSIGNED:
        panoptes_subject_set_workflows: List[PanoptesWorkflow] = []
    else:
        panoptes_subject_set_workflows = PanoptesSubjectSet.find(panoptes_subject_set_id).raw["links"].get("workflows", [])
    if len(panoptes_subject_set_workflows) == 0:
        panoptes_workflow_id: int|None = NO_WORKFLOW_ASSIGNED
    else:
        panoptes_workflow_id: int|None = int(panoptes_subject_set_workflows[0])

    sonification_uuid: str = panoptes_subject.metadata.get("uuid", None)

    return panoptes_subject_set_id, panoptes_workflow_id, sonification_uuid


def __add_subject_set(
        session: Session,
        panoptes_subject_set: PanoptesSubjectSet,
        panoptes_workflow_id: int | None
) -> None:
    """
    Add a subject set to a database session.

    The database is queried to ensure that duplicates are not added.

    Parameters
    ----------
    session : Session
        A database session to edit.
    panoptes_subject_set : PanoptesSubjectSet
        The Panoptes subject set to potentially add to the database.
    panoptes_workflow_id : int | None
        The ID of the workflow the subject set is linked to.
    """

    existing_subject_sets = (
        session.query(LocalSubjectSet).filter(LocalSubjectSet.zooniverse_subject_set_id == int(panoptes_subject_set.id))
        # .filter(LocalSubjectSet.workflow_id == workflow_id)
    ).count()

    if existing_subject_sets > 0:
        return

    priority = panoptes_subject_set.metadata.get(
        "#priority",
        # fall back is to get the priority from the name of the subject set
        # TODO, let's be smarter about this in the future and search for a substring
        "".join([char for char in panoptes_subject_set.display_name.split()[-1] if char.isdigit()]),
    )

    session.add(
        LocalSubjectSet(
            zooniverse_subject_set_id=int(panoptes_subject_set.id),
            priority=int(priority) if priority else None,  # ternary in case of no priority found
            zooniverse_workflow_id=panoptes_workflow_id,
            zooniverse_project_id=int(panoptes_subject_set.links.project.id),
            display_name=panoptes_subject_set.display_name,
        )
    )


def __clean_up_old_linked_subject_sets(
        session: Session,
        panoptes_subject_set:
        PanoptesSubjectSet
) -> None:
    """
    Remove entries which have a non-NULL workflow ID.

    This exists because subject sets which become unlinked would not have their
    previous non-NULL entries removed. We should only get here when a workflow
    has no linked workflows.

    Parameters
    ----------
    session : Session
        The database session to edit.
    panoptes_subject_set : PanoptesSubjectSet
        The subject set to try and remove non-NULL entries from.
    """
    # ...links.workflows does not support len(), so have to count like this
    workflow_count = 0
    for _ in panoptes_subject_set.links.workflows:
        workflow_count += 1

    if workflow_count == 0:
        logger.debug(
            f"Subject set {panoptes_subject_set.id} is not assigned to any workflows"
        )
        return
    if workflow_count > 0:
        raise ValueError("This function does not support subject sets which are linked to multiple workflows")

    subject_set_query = session.query(LocalSubjectSet).filter(LocalSubjectSet.zooniverse_subject_set_id == int(panoptes_subject_set.id))
    if subject_set_query.count() > 1:
        # pylint: disable=singleton-comparison
        non_null_workflow_query = subject_set_query.filter(LocalSubjectSet.zooniverse_workflow_id is not None)
        for row in non_null_workflow_query:
            session.delete(row)
        session.commit()


# Public functions -------------------------------------------------------------
def sync_subject_database_with_zooniverse(
    session: Session,
    panoptes_subjects_from_zooniverse: List[PanoptesSubject],
    num_panoptes_subjects: int,
    commit_frequency: int | None = 250,
) -> None:
    """
    Add subjects to the database which have already been uploaded to Zooniverse.

    The subjects to be added need to be passed to this function. The subjects
    can be gotten using something like `panoptes_client.Subject.find()` or
    `panoptes_client.SubjectSet.subjects`.

    This function is different to :meth:`update_subjects_database`, as it makes
    a number of assumptions about data existing and where it exists which is
    not the case in :meth:`update_subjects_database`.
    When debug logging is enabled, multiple counters are printed to show how
    many subjects were found, added and linked/added to the subject database.

    TODO: this function could do with a refactor

    Parameters
    ----------
    session: Session
        The database session to write to.
    panoptes_subjects_from_zooniverse:
        A list of Zooniverse Subjects to process.
    num_panoptes_subjects:
        The number of subjects to process.
    commit_frequency: int
        The frequency of which to commit to the database.
    """
    logger.debug(f"Processed 0/{num_panoptes_subjects} (0%) Zooniverse subjects", )
    for i, panoptes_subject in enumerate(
        tqdm(
            panoptes_subjects_from_zooniverse,
            desc="Syncing Zooniverse subjects with MoleDB",
            unit="subjects",
            total=num_panoptes_subjects,
            leave=logger.level <= logging.INFO,
            disable=logger.level > logging.INFO,
        )
    ):
        panoptes_subject_set_id, panoptes_workflow_id, sonification_uuid = __check_panoptes_subject_valid(panoptes_subject)
        if sonification_uuid is None:  # don't know what to do with stamps with no names
            continue

        sonification_query: Query[Sonification] = session.query(Sonification.filter(Sonification.uuid == sonification_uuid))
        if sonification_query.count() != 1:
            continue

        try:
            retired_status: bool = bool(panoptes_subject.subject_workflow_status(panoptes_workflow_id).raw["retired_at"])
        except StopIteration:  # stop iteration raised when subject is not in the workflow
            retired_status: bool = False

        new_row: LocalSubject = LocalSubject(
            zooniverse_subject_id=int(panoptes_subject.id),
            zooniverse_subject_set_id=panoptes_subject_set_id,
            sonification_id=int(sonification_query.first().id),
            retired=retired_status,
        )

        local_subject_query: Query[LocalSubject] = session.query(LocalSubject).filter(LocalSubject.zooniverse_subject_id == panoptes_subject.id)
        num_local_subjects_existing: int = local_subject_query.count()

        if num_local_subjects_existing > 1:
            raise ValueError(f"Subject {panoptes_subject.id} has multiple subjects in the database, please fix this")

        if num_local_subjects_existing:
            local_subject: LocalSubject = local_subject_query.first()
            local_subject.subject_set_id = panoptes_subject_set_id
            local_subject.project_id = panoptes_subject.links.project.id
            local_subject.workflow_id = panoptes_workflow_id
            local_subject.retired = retired_status
        else:
            session.add(new_row)

        if i % commit_frequency == 0:
            commit_database(session)
            logger.debug(
                f"Processed {i}/{num_panoptes_subjects} ({100 * i / num_panoptes_subjects}%) Zooniverse subjects",
            )

    commit_database(session)
    logger.debug(f"Processed {num_panoptes_subjects}/{num_panoptes_subjects} (100%) Zooniverse subjects")


def remove_broken_local_subject_sets_from_database(
        session: Session
) -> None:
    """
    Removes subject sets with no Zooniverse counterpart from the local DB.

    Checks local subject sets to see if there's a matching set on the Zooniverse,
    and removes them if there isn't.

    Parameters
    ----------
    session: Session
        A SQLAlchemy database session to the MoleMarshal database.
    """

    for local_subject_set in tqdm(
        query := session.query(LocalSubjectSet),
        total=query.count(),
        desc="Checking correctness of database",
        unit="row",
        leave=logger.level <= logging.INFO,
        disable=logger.level > logging.INFO,
    ):
        # if an api exception is raised by panoptes, the subject set can't be
        # found because it has been deleted on zooniverse
        try:
            _zoo = PanoptesSubjectSet.find(local_subject_set.zooniverse_subject_set_id)
            # this is for when a subject set has moved workflows or has been
            # unlinked -- not sure if we need it
            # zoo_workflows = [int(workflow) for workflow in _zoo.links.workflows]
            # if subject_set.workflow_id not in zoo_workflows:
            #     session.delete(subject_set)
        except PanoptesAPIException:
            session.delete(local_subject_set)

    session.commit()


def sync_local_subject_set_database_with_zooniverse(
        session: Session,
        panoptes_subject_sets_to_add: List[PanoptesSubjectSet],
        num_panoptes_subject_sets_to_add: int,
        _commit_frequency: int = 250
) -> None:
    """
    Add subject sets to the database which have been uploaded to Zooniverse.

    Panoptes subject sets which have been uploaded to Zooniverse are processed and
    updated in the database. If the priority of the subject set cannot be found
    either in the metadata or in the name of the subject set, then a null value
    is used instead.

    Parameters
    ----------
    session: Session
        A SQLAlchemy database session to the MoleMarshal database.
    panoptes_subject_sets_to_add: List[SubjectSet]
        A list containing SubjectSet's to add to the database.
    num_panoptes_subject_sets_to_add: int
        The number of subject sets which will be added.
    _commit_frequency: int
        The frequency to commit changes. Currently unused.

    Raises
    ------
    ValueError
        Raised when an unknown source is provided.
    """
    remove_broken_local_subject_sets_from_database(session)

    for panoptes_subject_set in tqdm(
        panoptes_subject_sets_to_add,
        total=num_panoptes_subject_sets_to_add,
        desc="Syncing Zooniverse subject sets with MoleDB",
        unit="subject sets",
        leave=logger.level <= logging.INFO,
        disable=logger.level > logging.INFO,
    ):
        # this should catch subject sets not linked to a workflow, but still
        # in a project
        if len(list(panoptes_subject_set.links.workflows)) == 0:
            __add_subject_set(session, panoptes_subject_set, None)
            __clean_up_old_linked_subject_sets(session, panoptes_subject_set)
        else:
            # this extra loop allows us to have the same subject set in multiple
            # workflows
            for panoptes_workflow in panoptes_subject_set.links.workflows:
                __add_subject_set(session, panoptes_subject_set, int(panoptes_workflow.id))

    session.commit()
