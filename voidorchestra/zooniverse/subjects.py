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
from voidorchestra.db import (
    LightcurveCollection,
    Sonification,
    SonificationProfile,
    Subject as LocalSubject,
    commit_database,
    connect_to_database_engine,
)
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

        # try:
        #     retired_status: bool = bool(panoptes_subject.subject_workflow_status(panoptes_workflow_id).raw["retired_at"])
        # except StopIteration:  # stop iteration raised when subject is not in the workflow
        #     retired_status: bool = False

        retired_status: bool = False

        # Create a matching local Subject
        local_subject: LocalSubject = LocalSubject(
            sonification_id=sonification.id,
            zooniverse_project_id=panoptes_project_id,
            zooniverse_subject_id=panoptes_subject.id,
            zooniverse_subject_set_id=panoptes_subject_set_id,
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


def upload_sonifications_to_zooniverse(
    panoptes_project_id: int,
    commit_frequency: int | None = 250,
) -> None:
    """
    Update a subject set with more subjects.

    This has been designed to work with just URL manifests, therefore you cannot
    add subjects which are not URLS such as raw images.

    Adds all sonifications in the database to a subject set based on their sonification profile.

    Parameters
    ----------
    panoptes_project_id: int
        The ID for the project on the Zooniverse.
    commit_frequency: int
        The frequency at which to commit entries to the database. Default value
        is 1000.

    Returns
    -------
    panoptes_subject_set: PanoptesSubjectSet
        The updated panoptes subject set.
    """
    if not panoptes_project_id:
        panoptes_project_id = config["ZOONIVERSE"]["project_id"]
    if commit_frequency <= 0:
        raise ValueError("Commit frequency should be positive and non-zero")

    panoptes_project: PanoptesProject = open_zooniverse_project(panoptes_project_id)
    num_subject_sets_added_to: int = 0
    num_subjects_added_across_subject_sets: int = 0

    with Session(
        engine := connect_to_database_engine(config_paths["database"]),
        info={"url": engine.url}
    ) as session:
        for sonification_profile in session.query(SonificationProfile).all():
            sonifications: List[Sonification] = sonification_profile.sonifications

            if not len(sonifications):
                logger.debug(
                    f"{sonification_profile}: Has no sonifications, continuing to next."
                )
                continue
            else:
                logger.debug(
                    f"{sonification_profile}: Sonifications - {sonifications}."
                )

            for lightcurve_collection in session.query(LightcurveCollection).all():
                panoptes_subject_set: PanoptesSubjectSet = get_named_panoptes_subject_set_in_panoptes_project(
                    panoptes_project,
                    proposed_subject_set_name=f"{sonification_profile} - {lightcurve_collection}"
                )
                sonifications_in_subject_set: List[Sonification] = [
                    sonification for sonification in sonifications if sonification.lightcurve.lightcurve_collection == lightcurve_collection
                ]

                # Get the UUIDs of the local subjects
                uuids_of_local_subjects_in_subject_set: List[str] = [
                    local_subject.sonification.uuid
                    for local_subject in session.query(LocalSubject).filter(
                        LocalSubject.zooniverse_subject_set_id == panoptes_subject_set.id
                    )
                ]
                if len(uuids_of_local_subjects_in_subject_set):
                    logger.debug(
                        f"{sonification_profile}: {len(uuids_of_local_subjects_in_subject_set)} subjects already in subject set."
                    )

                sonifications_to_add: List[Sonification] = [
                    sonification for sonification in sonifications_in_subject_set if sonification.uuid not in uuids_of_local_subjects_in_subject_set
                ]

                total_sonifications: int = len(sonifications_to_add)
                if not total_sonifications:
                    logger.info(
                        f"{sonification_profile}: No sonifications to upload"
                    )
                    continue

                logger.debug(
                    f"{panoptes_subject_set}: {total_sonifications} to be added."
                )
                num_subject_sets_added_to += 1
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

                        sonification_url: str = f"{config['ZOONIVERSE']['host_address']}/{sonification.path_video}"

                        # check first if the subject exists in the database. If it does,
                        # then we will add the subject already in the server to the
                        # subject set, otherwise we will have to create a new subject
                        local_subject: LocalSubject|None = session.query(LocalSubject).filter(
                            LocalSubject.sonification_id == sonification.id
                        ).first()

                        if local_subject:
                            panoptes_subject: PanoptesSubject = PanoptesSubject.find(local_subject.zooniverse_subject_id)
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

                if len(new_panoptes_subjects) > 0:
                    panoptes_subject_set.add(new_panoptes_subjects)
                    panoptes_subject_set.save()
                    session.commit()  # as we may have updated some parts of a stamp entry

                    logger.debug(
                        f"{panoptes_subject_set}: Updated with {len(new_panoptes_subjects)} subjects."
                    )

                    add_panoptes_subjects_to_local_subject_database(
                        session,
                        panoptes_project.id,
                        panoptes_subject_set.id,
                        new_panoptes_subjects,
                        commit_frequency,
                    )
                    num_subjects_added_across_subject_sets += len(new_panoptes_subjects)
        else:
            logger.info(f"No new Panoptes subjects.")

    logger.debug(
        f"Uploaded {num_subjects_added_across_subject_sets} sonifications to "
        f"{num_subject_sets_added_to} subject sets on the Zooniverse."
    )
