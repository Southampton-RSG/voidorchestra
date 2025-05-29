#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# Panoptes client https://panoptes-python-client.readthedocs.io/en/latest/

"""
Subjects and the subject sets they belong to are the very heart of any
Zooniverse project. This module includes functions which create subjects
and subject sets, as well as a number of functions for keeping a database of
subjects up to date with the local and remote stamps/subjects.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from panoptes_client import Project, Subject, SubjectSet
from panoptes_client.panoptes import PanoptesAPIException
from sqlalchemy.orm import Session
from tqdm import tqdm

import voidorchestra.db
import voidorchestra
import voidorchestra.log
import voidorchestra.zooniverse.zooniverse
from voidorchestra.zooniverse import workflows
from voidorchestra.zooniverse.subject_sets import get_named_subject_set_in_project

logger: logging.Logger = voidorchestra.log.get_logger(__name__.replace(".", "-"))


# Public functions ------------------------------------------------------------


# pylint: disable=too-many-arguments
def add_subjects_to_subject_database(
    session: Session,
    project_id: str | int,
    subject_set_id: str | int,
    workflow_id: str | int,
    new_subjects: List[Subject],
    commit_frequency: int = 1000,
) -> None:
    """Add subjects to the subjects database.

    To add a subject, its metadata is checked against the stamps table to ensure
    that there is a corresponding stamp and to ensure that the metadata is
    correct. If there is already a subject for that stamp, then that entry
    is updated with the new subject. Otherwise a new entry is created.

    Parameters
    ----------
    session: Session
        The database session to interact wth the database.
    project_id: str | int
        The ID of the project in Zooniverse.
    subject_set_id: str | int
        The ID of the subject set the subjects were uploaded to.
    workflow_id: str | int
        The ID of the workflow the subject set will be assigned to.
    new_subjects: List[Subject]
        A list containing new Subjects to be added to the database.
    commit_frequency: int
        The frequency of which to commit new entries to the database.
    """
    subjects_to_remove = []
    num_subjects = len(new_subjects)

    for i, subject in enumerate(
        tqdm(
            new_subjects,
            "Adding subjects to MoleDB",
            unit="subjects",
            leave=logger.level <= logging.INFO,
            disable=logger.level > logging.INFO,
        )
    ):
        subject_stamp_name = subject.metadata["name"]
        stamp = session.query(voidorchestra.db.Stamp).filter(voidorchestra.db.Stamp.stamp_name == subject_stamp_name).first()

        if not stamp:
            logger.warning("Subject %s (%s) has no stamp in the database", subject.id, subject_stamp_name)
            subjects_to_remove.append(subject)
            continue

        try:
            retired_status = bool(subject.subject_workflow_status(workflow_id).raw["retired_at"])
        except StopIteration:  # stop iteration raised when subject is not in the workflow
            retired_status = False

        subject_entry = voidorchestra.db.Subject(
            subject_id=subject.id,
            stamp_id=stamp.stamp_id,
            subject_set_id=subject_set_id,
            project_id=project_id,
            workflow_id=workflow_id,
            retired=retired_status,
        )

        # check if it exists, and merge if we do. first() is fine here because
        # stamp_id is part of the composite primary key of the subjects table,
        # so there should only be one returned anyway
        subject_exists = bool(session.query(voidorchestra.db.Subject).filter(voidorchestra.db.Subject.sonification_id == sonification.sonification_id).first())

        if subject_exists:
            session.merge(subject_entry)
        else:
            session.add(subject_entry)

        if i % commit_frequency == 0:
            voidorchestra.db.commit_database(session)
            logger.debug(
                "Processed %d/%d (%.0f%%) subjects",
                i + 1,
                num_subjects,
                (i + 1) / num_subjects * 100,
            )

    voidorchestra.db.commit_database(session)

    logger.debug(
        "Processed %d/%d (100%%) subjects",
        num_subjects,
        num_subjects,
    )

    if subjects_to_remove:
        subject_set = SubjectSet.find(subject_set_id)
        subject_set.remove(subjects_to_remove)
        subject_set.save()

    logger.info(
        "Added %d subjects to %s", len(new_subjects) - len(subjects_to_remove), session.info.get("url", "database")
    )


def add_subjects_to_subject_set(
    project: Project,
    subject_set_id: str | int,
    workflow_id: str | int,
    commit_frequency: int | None = 250,
) -> SubjectSet:
    """Update a subject set with more subjects.

    This has been designed to work with just URL manifests, therefore you cannot
    add subjects which are not URLS such as raw images.

    The default behavior is to add all stamps in the stamps database to the
    subject set. If this is not desired, then you can pass `stamp_subset` which
    is either a file path to a directory or to a file containing stamps. Then
    only this subset of stamps will be uploaded. Note that the stamp subset also
    have to be in the stamp database.

    Parameters
    ----------
    project: Project
        The project class for the project to add the subject set to.
    subject_set_id: str
        The ID of the subject set to add to.
    workflow_id: int
        The ID of the subject set to link the workflow to.
    stamp_subset: str
        A directory containing stamps to add, or a file containing file paths
        on each line. These stamps will be added instead of the entire
        database of stamps.
    commit_frequency: int
        The frequency at which to commit entries to the database. Default value
        is 1000.

    Returns
    -------
    subject_set: SubjectSet
        The updated subject set.
    """
    if commit_frequency <= 0:
        raise ValueError("Commit frequency should be positive and non-zero")

    try:
        subject_set = SubjectSet.find(subject_set_id)
    except PanoptesAPIException as exception:
        raise ValueError(f"Unable to find a subject set with id {subject_set_id}") from exception

    with Session(
        engine := voidorchestra.db.connect_to_database_engine(voidorchestra.config["PATHS"]["database"]), info={"url": engine.url}
    ) as session:
        names_of_subjects_in_set = [
            subject.stamp.stamp_name
            for subject in session.query(voidorchestra.db.Subject).filter(voidorchestra.db.Subject.subject_set_id == subject_set.id)
        ]

        logger.debug("%d subjects already in subject set %d", len(names_of_subjects_in_set), subject_set_id)

        stamps_to_add = session.query(voidorchestra.db.Stamp)
        total_images = stamps_to_add.count()

        if total_images == 0:
            raise ValueError("No stamp images found in database or provided stamp subset")

        logger.debug("%d images to be added to subject set %d", total_images, subject_set_id)

        new_subjects = []

        with Subject.async_saves():  # using async save should speed this up, I hope
            for i, stamp in enumerate(
                tqdm(
                    stamps_to_add,
                    desc="Uploading stamps to Zooniverse",
                    total=total_images,
                    unit="stamps",
                    leave=logger.level <= logging.INFO,
                    disable=logger.level > logging.INFO,  # disable tqdm output for debug output
                )
            ):
                # if the stamp is in the subject set, then don't need to do
                # anything, and we assume that it's already in the database
                if stamp.stamp_name in names_of_subjects_in_set:
                    logger.debug("Skipping stamp %d as it's already in subject set", i)
                    continue

                # create the URL for the stamp image if that doensn't exist and
                # change any image_type entries to jpeg, as image/jpg is not a
                # valid MIME type apparently
                if not stamp.url:
                    stamp_url = stamp.url = f"{voidorchestra.config['ZOONIVERSE']['host_address']}/{stamp.filepath}"
                else:
                    stamp_url = stamp.url
                if stamp.image_type == "jpg":
                    stamp_image_type = stamp.image_type = "jpeg"
                else:
                    stamp_image_type = stamp.image_type

                # check first if the subject exists in the database. If it does,
                # then we will add the subject already in the server to the
                # subject set, otherwise we will have to create a new subject
                subject_query = session.query(voidorchestra.db.Subject).filter(voidorchestra.db.Subject.stamp_id == stamp.stamp_id).first()

                if subject_query:
                    subject = Subject.find(subject_query.subject_id)
                else:
                    subject = Subject()
                    subject.links.project = project
                    location = {f"image/{stamp_image_type}": stamp_url}
                    metadata = {
                        "name": stamp.stamp_name,
                        "patient": stamp.patient.patient_name,
                        "date": str(stamp.date),
                        "filepath": str(stamp.filepath),
                        "description": stamp.description if stamp.description else "",
                    }
                    subject.add_location(location)
                    subject.metadata.update(metadata)
                    subject.save()

                    logger.debug(
                        "Subject %d: location %s metadata %s subject %s",
                        i,
                        location,
                        metadata,
                        subject,
                    )

                new_subjects.append(subject)

            session.commit()  # as we may have updated some parts of a stamp entry

        if len(new_subjects) > 0:
            subject_set.add(new_subjects)
            subject_set.save()
            logger.debug("Subject set %s updated with %d subjects", subject_set.display_name, len(new_subjects))
            add_subjects_to_subject_database(
                session,
                project.id,
                subject_set.id,
                workflow_id,
                new_subjects,
                commit_frequency,
            )
        else:
            logger.info("No new subjects added to subject set %s", subject_set_id)

    return subject_set


def upload_to_subject_set(
    project_id: str | int | None = None,
    workflow_id: str | int | None = None,
    subject_set_id: str | int | None = None,
    subject_set_name: str | None = None,
    # stamp_subset: str | Path | None = None,
    commit_frequency: int = 250,
) -> None:
    """Modify a subject set with new subjects.

    This is a top level steering function which handles opening the project,
    creating/getting a subject set, updating the subject set with subjects
    and finally assigning that subject set to a workflow.

    All arguments are optional, so you do not need to provide any IDs. They are
    still here in case any finer control is needed, such as adding to a specific
    subject set.

    Parameters
    ----------
    project_id: str | int
        The Zooniverse project ID.
    workflow_id: str | int
        The ID of the workflow to attach the subjects to.
    subject_set_id: str | int | None
        The ID of the subject set to modify. If this argument is not provided,
        then the subject set named "Mole molemarshal.db.stamp.Stamps" will either be created or
        found.
    subject_set_name: str | None
        The name of the subject set to modify. If this argument is not provided,
        then the subject set named "Mole molemarshal.db.stamp.Stamps" will either be created or
        found.
    stamp_subset: str | Path
        A file path to a directory containing stamps, or a file path to a file
        containing file paths to stamps on each line. The stamps in the subset
        **must** be in the stamp database.
    commit_frequency: int
        The frequency of which to commit changes to the database.
    """
    if not project_id:
        project_id = voidorchestra.config["ZOONIVERSE"]["project_id"]
    if not workflow_id:
        workflow_id = voidorchestra.config["ZOONIVERSE"]["workflow_id"]
    if not subject_set_id and not subject_set_name:
        subject_set_id = voidorchestra.config["ZOONIVERSE"]["subject_set_id"]

    project = voidorchestra.zooniverse.zooniverse.open_zooniverse_project(project_id)

    # when subject_set_id is not provided or subject_set_name is provided, we
    # will get (or create) the subject set either named "Mole Stamps" or
    # whatever subject_set_name is. We need to also do this to get hold of the
    # subject set ID
    if subject_set_id is None or subject_set_name is not None:
        subject_set = get_named_subject_set_in_project(project, subject_set_name if subject_set_name else "Mole Stamps")
        subject_set_id = subject_set.id

    subject_set = add_subjects_to_subject_set(
        project,
        subject_set_id,
        workflow_id,
        # stamp_subset,
        commit_frequency,
    )

    # assign workflow to subject set, don't need to guard this as Zooniverse is
    # smart enough to not assign duplicate workflows
    workflow = workflows.get_workflow(workflow_id)
    workflows.assign_workflow_to_subject_set(workflow, subject_set)
