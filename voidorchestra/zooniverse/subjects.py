#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Panoptes client https://panoptes-python-client.readthedocs.io/en/latest/
"""
Subjects and the subject sets they belong to are the very heart of any
Zooniverse project. This module includes functions which create subjects
and subject sets, as well as a number of functions for keeping a database of
subjects up to date with the local and remote stamps/subjects.
"""
import logging
from logging import Logger
from typing import List

from panoptes_client import Project as PanoptesProject, Subject as PanoptesSubject, SubjectSet as PanoptesSubjectSet, Workflow as PanoptesWorkflow
from panoptes_client.panoptes import PanoptesAPIException
from sqlalchemy.orm import Query, Session
from tqdm import tqdm

from voidorchestra import config, config_paths
from voidorchestra.db import Sonification, Subject as LocalSubject, commit_database, connect_to_database_engine
from voidorchestra.log import get_logger
from voidorchestra.zooniverse.subject_sets import get_named_panoptes_subject_set_in_panoptes_project
from voidorchestra.zooniverse.workflows import assign_panoptes_workflow_to_panoptes_subject_set, get_panoptes_workflow
from voidorchestra.zooniverse.zooniverse import open_zooniverse_project

logger: Logger = get_logger(__name__.replace(".", "-"))


# Public functions ------------------------------------------------------------
def add_panoptes_subjects_to_local_subject_database(
    session: Session,
    panoptes_project_id: str | int,
    panoptes_subject_set_id: str | int,
    panoptes_workflow_id: str | int,
    new_panoptes_subjects: List[PanoptesSubject],
    commit_frequency: int = 1000,
) -> None:
    """
    Add subjects to the subjects database.

    To add a subject, its metadata is checked against the stamps table to ensure
    that there is a corresponding sonification and to ensure that the metadata is
    correct. If there is already a subject for that sonification, then that entry
    is updated with the new subject. Otherwise, a new entry is created.

    Parameters
    ----------
    session: Session
        The database session to interact wth the database.
    panoptes_project_id: str | int
        The ID of the project in Zooniverse.
    panoptes_subject_set_id: str | int
        The ID of the subject set the subjects were uploaded to.
    panoptes_workflow_id: str | int
        The ID of the workflow the subject set will be assigned to.
    new_panoptes_subjects: List[PanoptesSubject]
        A list containing new Panoptes Subjects to be added to the database.
    commit_frequency: int
        The frequency of which to commit new entries to the database.
    """
    panoptes_subjects_to_remove: List[PanoptesSubject] = []
    num_panoptes_subjects: int = len(new_panoptes_subjects)

    for i, panoptes_subject in enumerate(
        tqdm(
            new_panoptes_subjects,
            "Adding subjects to Void Orchestra",
            unit="subjects",
            leave=logger.level <= logging.INFO,
            disable=logger.level > logging.INFO,
        )
    ):
        # Match the Panoptes subject to a local sonification.
        subject_sonification_uuid: str = panoptes_subject.metadata["uuid"]
        sonification: Sonification|None = session.query(Sonification).filter(Sonification.uuid == subject_sonification_uuid).first()

        if not sonification:
            # Something has gone wrong, we need to strip this subject out from Panoptes.
            logger.warning(
                f"Subject {panoptes_subject.id} ({subject_sonification_uuid}) has no sonifications in the database",
            )
            panoptes_subjects_to_remove.append(panoptes_subject)
            continue

        try:
            retired_status: bool = bool(panoptes_subject.subject_workflow_status(panoptes_workflow_id).raw["retired_at"])
        except StopIteration:  # stop iteration raised when subject is not in the workflow
            retired_status: bool = False

        # Create a matching local Subject
        local_subject: LocalSubject = LocalSubject(
            sonification_id=sonification.sonification_id,
            zooniverse_project_id=panoptes_project_id,
            zooniverse_subject_id=panoptes_subject.id,
            zooniverse_subject_set_id=panoptes_subject_set_id,
            zooniverse_workflow_id=panoptes_workflow_id,
            retired=retired_status,
        )

        # check if it exists, and merge if we do. first() is fine here because
        # sonification_id is part of the composite primary key of the subjects table,
        # so there should only be one returned anyway
        local_subject_exists: bool = bool(
            session.query(LocalSubject).filter(LocalSubject.sonification == sonification).first()
        )

        if local_subject_exists:
            session.merge(local_subject)
        else:
            session.add(local_subject)

        if i % commit_frequency == 0:
            commit_database(session)
            logger.debug(
                f"Processed {i+1}/{num_panoptes_subjects} ({100 * (i+1)/num_panoptes_subjects}%) subjects.",
        )

    commit_database(session)

    logger.debug(
        f"Processed {num_panoptes_subjects}/{num_panoptes_subjects} (100%) subjects.",
    )

    if panoptes_subjects_to_remove:
        panoptes_subject_set: PanoptesSubject = PanoptesSubjectSet.find(panoptes_subject_set_id)
        panoptes_subject_set.remove(panoptes_subjects_to_remove)
        panoptes_subject_set.save()

    logger.info(
        f"Added {len(new_panoptes_subjects) - len(panoptes_subjects_to_remove)} subjects to {session.info.get("url", "database")}."
    )


def add_panoptes_subjects_to_panoptes_subject_set(
    panoptes_project: PanoptesProject,
    panoptes_subject_set_id: str | int,
    panoptes_workflow_id: str | int,
    commit_frequency: int | None = 250,
) -> PanoptesSubjectSet:
    """
    Update a subject set with more subjects.

    This has been designed to work with just URL manifests, therefore you cannot
    add subjects which are not URLS such as raw images.

    The default behavior is to add all sonifications in the sonification database to the
    subject set. If this is not desired, then you can pass `` which
    is either a file path to a directory or to a file containing stamps. Then
    only this subset of stamps will be uploaded. Note that the stamp subset also
    have to be in the stamp database.

    Parameters
    ----------
    panoptes_project: PanoptesProject
        The project class for the project to add the subject set to.
    panoptes_subject_set_id: str
        The ID of the subject set to add to.
    panoptes_workflow_id: int
        The ID of the subject set to link the workflow to.
    commit_frequency: int
        The frequency at which to commit entries to the database. Default value
        is 1000.

    Returns
    -------
    panoptes_subject_set: PanoptesSubjectSet
        The updated panoptes subject set.
    """
    if commit_frequency <= 0:
        raise ValueError("Commit frequency should be positive and non-zero")

    try:
        panoptes_subject_set = PanoptesSubjectSet.find(panoptes_subject_set_id)
    except PanoptesAPIException as exception:
        raise ValueError(
            f"Unable to find a subject set with id {panoptes_subject_set_id}"
        ) from exception

    with Session(
        engine := connect_to_database_engine(config_paths["database"]),
        info={"url": engine.url}
    ) as session:
        # Get the UUIDs of the local subjects
        uuids_of_subjects_in_set: List[str] = [
            local_subject.sonification.uuid
            for local_subject in session.query(LocalSubject).filter(LocalSubject.panoptes_subject_set_id == panoptes_subject_set.id)
        ]

        logger.debug(
            f"{len(uuids_of_subjects_in_set)} subjects already in subject set {panoptes_subject_set_id}."
        )
        sonifications_to_add: Query[Sonification] = session.query(Sonification)

        if total_sonifications := sonifications_to_add.count():
            raise ValueError("No sonifications found in database or provided sonification subset")

        logger.debug(
            f"{total_sonifications} to be added to subject set {panoptes_subject_set_id}"
        )

        new_panoptes_subjects: List[PanoptesSubject] = []

        with PanoptesSubject.async_saves():  # using async save should speed this up, I hope
            for i, sonification in enumerate(
                tqdm(
                    sonifications_to_add,
                    desc="Uploading sonifications to Zooniverse",
                    total=total_sonifications,
                    unit="sonifications",
                    leave=logger.level <= logging.INFO,
                    disable=logger.level > logging.INFO,  # disable tqdm output for debug output
                )
            ):
                # if the stamp is in the subject set, then don't need to do
                # anything, and we assume that it's already in the database
                if sonification.uuid in uuids_of_subjects_in_set:
                    logger.debug(f"Skipping sonification {i} as it's already in subject set.")
                    continue

                sonification_url: str = f"{config['ZOONIVERSE']['host_address']}/{sonification.path_video}"

                # check first if the subject exists in the database. If it does,
                # then we will add the subject already in the server to the
                # subject set, otherwise we will have to create a new subject
                local_subject: LocalSubject = session.query(LocalSubject).filter(
                    LocalSubject.sonification_id == sonification.id
                ).first()

                if local_subject:
                    panoptes_subject: PanoptesSubject = PanoptesSubject.find(local_subject.panoptes_subject_id)
                else:
                    panoptes_subject: PanoptesSubject = PanoptesSubject()
                    panoptes_subject.links.project = panoptes_project
                    location = {"video/mp4": sonification_url}
                    metadata = {
                        "uuid": sonification.uuid,
                    }
                    panoptes_subject.add_location(location)
                    panoptes_subject.metadata.update(metadata)
                    panoptes_subject.save()

                    logger.debug(
                        f"Subject {i}: location {location}, metadata {metadata}, Panoptes subject {panoptes_subject}",
                    )

                new_panoptes_subjects.append(panoptes_subject)

            session.commit()  # as we may have updated some parts of a stamp entry

        if len(new_panoptes_subjects) > 0:
            panoptes_subject_set.add(new_panoptes_subjects)
            panoptes_subject_set.save()
            logger.debug(
                f"Subject set {panoptes_subject_set.display_name} updated with {len(new_panoptes_subjects)} subjects."
            )
            add_panoptes_subjects_to_local_subject_database(
                session,
                panoptes_project.id,
                panoptes_subject_set.id,
                panoptes_workflow_id,
                new_panoptes_subjects,
                commit_frequency,
            )
        else:
            logger.info(f"No new Panoptes subjects added to Panoptes subject set {panoptes_subject_set_id}.")

    return panoptes_subject_set


def upload_to_panoptes_subject_set(
    panoptes_project_id: str | int | None = None,
    panoptes_workflow_id: str | int | None = None,
    panoptes_subject_set_id: str | int | None = None,
    subject_set_name: str | None = None,
    commit_frequency: int = 250,
) -> None:
    """
    Modify a subject set with new subjects.

    This is a top level steering function which handles opening the project,
    creating/getting a subject set, updating the subject set with subjects
    and finally assigning that subject set to a workflow.

    All arguments are optional, so you do not need to provide any IDs. They are
    still here in case any finer control is needed, such as adding to a specific
    subject set.

    Parameters
    ----------
    panoptes_project_id: str | int
        The Zooniverse project ID.
    panoptes_workflow_id: str | int
        The ID of the workflow to attach the subjects to.
    panoptes_subject_set_id: str | int | None
        The ID of the subject set to modify. If this argument is not provided,
        then the subject set named "Default Subject Set" will either be created or
        found.
    subject_set_name: str | None
        The name of the subject set to modify. If this argument is not provided,
        then the subject set named "Default Subject Set" will either be created or
        found.
    commit_frequency: int
        The frequency of which to commit changes to the database.
    """
    if not panoptes_project_id:
        panoptes_project_id = config["ZOONIVERSE"]["project_id"]
    if not panoptes_workflow_id:
        panoptes_workflow_id = config["ZOONIVERSE"]["workflow_id"]
    if not panoptes_subject_set_id and not subject_set_name:
        panoptes_subject_set_id = config["ZOONIVERSE"]["subject_set_id"]

    panoptes_project: PanoptesProject = open_zooniverse_project(panoptes_project_id)

    # when subject_set_id is not provided or subject_set_name is provided, we
    # will get (or create) the subject set either named "Default Subject Set" or
    # whatever subject_set_name is. We need to also do this to get hold of the
    # subject set ID
    if panoptes_subject_set_id is None or subject_set_name is not None:
        panoptes_subject_set = get_named_panoptes_subject_set_in_panoptes_project(
            panoptes_project, subject_set_name if subject_set_name else "Default Subject Set"
        )
        panoptes_subject_set_id = panoptes_subject_set.id

    panoptes_subject_set: PanoptesSubjectSet = add_panoptes_subjects_to_panoptes_subject_set(
        panoptes_project,
        panoptes_subject_set_id,
        panoptes_workflow_id,
        commit_frequency,
    )

    # assign workflow to subject set, don't need to guard this as Zooniverse is
    # smart enough to not assign duplicate workflows
    panoptes_workflow: PanoptesWorkflow = get_panoptes_workflow(panoptes_workflow_id)
    assign_panoptes_workflow_to_panoptes_subject_set(panoptes_workflow, panoptes_subject_set)
