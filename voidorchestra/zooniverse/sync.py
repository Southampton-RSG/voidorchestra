#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
This module contains operations to sync with the Zooniverse database.
"""

from __future__ import annotations

import logging
from typing import List, Tuple

from sqlalchemy.orm import Session
from panoptes_client import Subject
from panoptes_client import SubjectSet
from panoptes_client.panoptes import PanoptesAPIException
from tqdm import tqdm

import voidorchestra.db

NO_SUBJECT_SET_ASSIGNED = None
NO_WORKFLOW_ASSIGNED = None

logger: logging.Logger = voidorchestra.log.get_logger(__name__.replace(".", "-"))


# Private functions ------------------------------------------------------------


def __check_subject_valid(subject: Subject) -> Tuple[int, int, str]:
    """Check that a subject has "valid" setup.

    Check if a subject has a valid setup by checking for the ID of the subject
    set and workflow it is assigned to -- in theory both of these can be
    NULL or None. Additionally also get the stamp name. If this is None, then
    something has gone wrong with the subject.

    Parameters
    ----------
    subject : Subject
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
    subject_set_ids = subject.raw["links"].get("subject_sets", [])
    if len(subject_set_ids) == 0:
        subject_set_id = NO_SUBJECT_SET_ASSIGNED
    elif len(subject_set_ids) > 1:
        raise ValueError(f"Subject {subject.id} is bad")
    else:
        subject_set_id = int(subject_set_ids[0])

    # check workflow config is valid
    if subject_set_id is NO_SUBJECT_SET_ASSIGNED:
        subject_set_workflows = []
    else:
        subject_set_workflows = SubjectSet.find(subject_set_id).raw["links"].get("workflows", [])
    if len(subject_set_workflows) == 0:
        workflow_id = NO_WORKFLOW_ASSIGNED
    else:
        workflow_id = int(subject_set_workflows[0])

    stamp_name = subject.metadata.get("name", None)

    return subject_set_id, workflow_id, stamp_name


def __add_subject_set(session: Session, subject_set: SubjectSet, workflow_id: int | None) -> None:
    """Add a subject set to a database session.

    The database is queried to ensure that duplicates are not added.

    Parameters
    ----------
    session : Session
        A database session to edit.
    subject_set : SubjectSet
        The subject set to potentially add to the database.
    workflow_id : int | None
        The ID of the workflow the subject set is linked to.
    """

    existing_subject_sets = (
        session.query(voidorchestra.db.SubjectSet).filter(voidorchestra.db.SubjectSet.subject_set_id == int(subject_set.id))
        # .filter(voidorchestra.db.SubjectSet.workflow_id == workflow_id)
    ).count()

    if existing_subject_sets > 0:
        return

    priority = subject_set.metadata.get(
        "#priority",
        # fall back is to get the priority from the name of the subject set
        # TODO, let's be smarter about this in the future and search for a substring
        "".join([char for char in subject_set.display_name.split()[-1] if char.isdigit()]),
    )

    session.add(
        voidorchestra.db.SubjectSet(
            subject_set_id=int(subject_set.id),
            priority=int(priority) if priority else None,  # ternary in case of no priority found
            workflow_id=workflow_id,
            project_id=int(subject_set.links.project.id),
            display_name=subject_set.display_name,
        )
    )


def __clean_up_old_linked_subject_sets(session: Session, subject_set: SubjectSet) -> None:
    """Remove entries which have a non-NULL workflow ID.

    This exists because subject sets which become unlinked would not have their
    previous non-NULL entries removed. We should only get here when a workflow
    has no linked workflows.

    Parameters
    ----------
    session : Session
        The database session to edit.
    subject_set : SubjectSet
        The subject set to try and remove non-NULL entries from.
    """
    # ...links.workflows does not support len(), so have to count like this
    workflow_count = 0
    for _ in subject_set.links.workflows:
        workflow_count += 1

    if workflow_count == 0:
        logger.debug("Subject set %s is not assigned to any workflows", subject_set.id)
        return
    if workflow_count > 0:
        raise ValueError("This function does not support subject sets which are linked to multiple workflows")

    subject_set_query = session.query(voidorchestra.SubjectSet).filter(voidorchestra.SubjectSet.subject_set_id == int(subject_set.id))
    if subject_set_query.count() > 1:
        # pylint: disable=singleton-comparison
        non_null_workflow_query = subject_set_query.filter(voidorchestra.SubjectSet.workflow_id != None)
        for row in non_null_workflow_query:
            session.delete(row)
        session.commit()


# Public functions -------------------------------------------------------------


def sync_subject_database_with_zooniverse(
    session: Session,
    subjects_from_zooniverse: List[Subject],
    num_subjects: int,
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
    subjects:
        A list of Zooniverse Subjects to process.
    num_subjects:
        The number of subjects to process.
    commit_frequency: int
        The frequency of which to commit to the database.
    """
    logger.debug("Processed 0/%d (0%%) Zooniverse subjects", num_subjects)
    for i, subject in enumerate(
        tqdm(
            subjects_from_zooniverse,
            desc="Syncing Zooniverse subjects with MoleDB",
            unit="subjects",
            total=num_subjects,
            leave=logger.level <= logging.INFO,
            disable=logger.level > logging.INFO,
        )
    ):
        subject_set_id, workflow_id, sonification_hash = __check_subject_valid(subject)
        if sonification_hash is None:  # don't know what to do with stamps with no names
            continue

        sonification_entry = session.query(voidorchestra.db.Sonification.filter(voidorchestra.db.Sonification.hash == sonification_hash))
        if sonification_entry.count() != 1:
            continue

        try:
            retired_status = bool(subject.subject_workflow_status(workflow_id).raw["retired_at"])
        except StopIteration:  # stop iteration raised when subject is not in the workflow
            retired_status = False

        new_row = voidorchestra.db.Subject(
            subject_id=int(subject.id),
            subject_set_id=subject_set_id,
            sonification_id=int(sonification_entry.first().sonification_id),
            retired=retired_status,
        )

        existing_subject = session.query(voidorchestra.db.Subject).filter(voidorchestra.db.Subject.subject_id == subject.id)
        num_existing = existing_subject.count()

        if num_existing > 1:
            raise ValueError(f"Subject {subject.id} has multiple subjects in the database, please fix this")

        if num_existing:
            existing_subject = existing_subject.first()
            existing_subject.subject_set_id = subject_set_id
            existing_subject.project_id = subject.links.project.id
            existing_subject.workflow_id = workflow_id
            existing_subject.retired = retired_status
        else:
            session.add(new_row)

        if i % commit_frequency == 0:
            voidorchestra.db.commit_database(session)
            logger.debug(
                "Processed %d/%d (%.0f%%) Zooniverse subjects",
                i,
                num_subjects,
                i / num_subjects * 100,
            )

    voidorchestra.db.commit_database(session)
    logger.debug("Processed %d/%d (100%%) Zooniverse subjects", num_subjects, num_subjects)


def remove_broken_subject_sets_from_database(session) -> None:
    """_summary_

    Parameters
    ----------
    session : _type_
        _description_
    """

    for subject_set in tqdm(
        query := session.query(voidorchestra.db.SubjectSet),
        total=query.count(),
        desc="Checking correctness of database",
        unit="row",
        leave=logger.level <= logging.INFO,
        disable=logger.level > logging.INFO,
    ):
        # if an api exception is raised by panoptes, the subject set can't be
        # found because it has been deleted on zooniverse
        try:
            _zoo = SubjectSet.find(subject_set.subject_set_id)
            # this is for when a subject set has moved workflows or has been
            # unlinked -- not sure if we need it
            # zoo_workflows = [int(workflow) for workflow in _zoo.links.workflows]
            # if subject_set.workflow_id not in zoo_workflows:
            #     session.delete(subject_set)
        except PanoptesAPIException:
            session.delete(subject_set)

    session.commit()


def sync_subject_set_database_with_zooniverse(
    session: Session, subject_sets_to_add: List[SubjectSet], num_to_add: int, _commit_frequency: int = 250
) -> None:
    """Add subject sets to the database which have been uploaded to Zooniverse.

    Subject sets which have been uploaded to Zooniverse are processed and
    updated in the database. If the priority of the subject set cannot be found
    either in the metadata or in the name of the subject set, then a null value
    is used instead.

    Given the small number of subject sets expected to exist, changes are
    committed only once. A variable to control the commit frequency exists,
    but is only there for consistency at the moment.

    Parameters
    ----------
    session: Session
        A SQLAlchemy database session to the MoleMarshal database.
    subject_sets_to_add: List[SubjectSet]
        A list containing SubjectSet's to add to the database.
    num_to_add: int
        The number of subject sets which will be added.
    _commit_frequency: int
        The frequency to commit changes. Currently unused.

    Raises
    ------
    ValueError
        Raised when an unknown source is provided.
    """

    remove_broken_subject_sets_from_database(session)

    for subject_set in tqdm(
        subject_sets_to_add,
        total=num_to_add,
        desc="Syncing Zooniverse subject sets with MoleDB",
        unit="subject sets",
        leave=logger.level <= logging.INFO,
        disable=logger.level > logging.INFO,
    ):
        # this should catch subject sets not linked to a workflow, but still
        # in a project
        if len(list(subject_set.links.workflows)) == 0:
            __add_subject_set(session, subject_set, None)
            __clean_up_old_linked_subject_sets(session, subject_set)
        else:
            # this extra loop allows us to have the same subject set in multiple
            # workflows
            for workflow in subject_set.links.workflows:
                __add_subject_set(session, subject_set, int(workflow.id))

    session.commit()
