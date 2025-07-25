# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The weight module handles assigning weights to subjects and to subject sets.
The weights are used to alter the probability of a subject or subject from a
subject set being shown to a user.
"""

import ast
import copy
import logging
import math
from logging import Logger
from typing import Iterable, List, Set

from panoptes_client import (
    Project as PanoptesProject,
    Subject as PanoptesSubject,
    SubjectSet as PanoptesSubjectSet,
    Workflow as PanoptesWorkflow,
)
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session
from tqdm import tqdm

from voidorchestra import config, config_paths
from voidorchestra.db import Subject as LocalSubject, SubjectSet as LocalSubjectSet, connect_to_database_engine
from voidorchestra.log import get_logger
from voidorchestra.zooniverse.sync import sync_local_subject_set_database_with_zooniverse
from voidorchestra.zooniverse.workflows import assign_panoptes_workflow_to_panoptes_subject_set, get_panoptes_workflow

logger: Logger = get_logger(__name__.replace(".", "-"))


# Private functions ------------------------------------------------------------
def __create_new_panoptes_subject_set(
    panoptes_project: PanoptesProject,
    panoptes_workflow: PanoptesWorkflow,
    display_name: str,
    priority: int,
    session: Session,
) -> PanoptesSubjectSet:
    """
    Create a new subject set on Zooniverse.

    Creates a new subject set with the given name on Zooniverse, and creates a
    new entry in the Void Orchestra database. This is why there are some seemingly
    redundant arguments.

    Parameters
    ----------
    panoptes_project : PanoptesProject
        A Project class for the project the subject set will be linked to.
    panoptes_workflow : PanoptesWorkflow
        A Workflow class for the workflow the subject set will be part of, or
        linked to.
    display_name : str
        The name of the new subject set.
    priority : int
        The priority ranking of the subject set.
    session : Session
        The database session to add the new subject set to.

    Returns
    -------
    panoptes_subject_set: PanoptesSubjectSet
        The created Panoptes-format subject set.
    """
    panoptes_subject_set: PanoptesSubjectSet = PanoptesSubjectSet()
    panoptes_subject_set.links.project = panoptes_project
    panoptes_subject_set.display_name = display_name
    panoptes_subject_set.save()

    session.add(
        LocalSubjectSet(
            zooniverse_subject_set_id=int(panoptes_subject_set.id),
            priority=int(priority),
            zooniverse_project_id=int(panoptes_project.id),
            zooniverse_workflow_id=int(panoptes_workflow.id),
            display_name=panoptes_subject_set.display_name,
        )
    )
    return panoptes_subject_set


def __binning_checkpoint(panoptes_subject_sets_to_update: List[PanoptesSubjectSet], session: Session) -> None:
    """
    Save changes to subject sets and the database session.

    For work going on in parallel on both local DB content and remote Zooniverse content.

    Parameters
    ----------
    panoptes_subject_sets_to_update : List[PanoptesSubjectSet]
        The subject sets to save changes to.
    session : Session
        The session to commit changes to.
    """
    for panoptes_subject_set in panoptes_subject_sets_to_update:
        panoptes_subject_set.save()

    session.commit()


def __create_missing_priority_local_subject_sets(
    session: Session,
    project_id: str | int,
    panoptes_workflow_id: str | int,
    num_sets: int,
    priorities: List[int] | None = None,
) -> List[LocalSubjectSet]:
    """
    Create new or find a subject set for the given priorities in the DB.

    Only the missing priority subject sets will be created or attempted to be
    found. This is done by figuring out the priority rankings which are missing.
    Newly created subject sets are added to the Void Orchestra database.

    Parameters
    ----------
    session : Session
        A ORM session to MoleDB.
    project_id : str | int
        The Zooniverse ID of the project subject sets will belong to.
    panoptes_workflow_id : str | int
        The Zooniverse ID of the workflow the subject sets will be assigned to.
    num_sets : int
        The number of subject sets which should exist.
    priorities : List[int] | None
        The requested priorities of the subject sets. The default value of None
        will create subject sets from range(1 num_sets + 1).

    Returns
    -------
    List[LocalSubjectSet]
        A list of local SubjectSet objects corresponding to the created/retrieved subject
        sets.
    """
    panoptes_project: PanoptesProject = PanoptesProject.find(project_id)
    panoptes_workflow: PanoptesWorkflow = get_panoptes_workflow(panoptes_workflow_id)

    # If priorities is not provided, then create a new collection of priority
    # subject sets. If it is provided, then we need to figure out which
    # priorities are missing using set().difference() on range(1, num_sets+1)
    if priorities:
        new_priorities_to_create: List[int] | Set[int] = set(range(1, num_sets + 1)).difference(priorities)
    else:
        new_priorities_to_create: List[int] = range(1, num_sets + 1)

    for priority in new_priorities_to_create:
        display_name: str = f"WF{panoptes_workflow.id} Sonification Priority #{priority}"

        # going to double check first that we def don't have a subject set which
        # already fulfills the purpose
        existing_local_subject_sets: Query[LocalSubjectSet] = (
            session.query(LocalSubjectSet)
            .filter(LocalSubjectSet.priority == int(priority))
            .filter(
                # pylint: disable=singleton-comparison
                or_(
                    LocalSubjectSet.zooniverse_workflow_id == int(panoptes_workflow.id),
                    LocalSubjectSet.zooniverse_workflow_id is None,
                )
            )
        )
        num_existing_local_subject_sets: int = existing_local_subject_sets.count()

        if num_existing_local_subject_sets:
            logger.debug(f"A subject set already exists with priority {priority} for workflow {panoptes_workflow.id}")
            for _iter in existing_local_subject_sets:
                if _iter.workflow_id is None:  # pylint: disable=singleton-comparison
                    index: int = [
                        subject_set.display_name for subject_set in panoptes_project.links.subject_sets
                    ].index(display_name)
                    panoptes_subject_set: PanoptesSubjectSet = panoptes_project.links.subject_sets[index]
                    _iter.workflow_id = int(panoptes_workflow.id)
            # this is purely a safety mechanism in-case the subject set is
            # somehow not found in the project, so we will create it
            if not panoptes_subject_set:
                panoptes_subject_set: PanoptesSubjectSet = __create_new_panoptes_subject_set(
                    panoptes_project, panoptes_workflow, display_name, priority, session
                )
        else:
            panoptes_subject_set: PanoptesSubjectSet = __create_new_panoptes_subject_set(
                panoptes_project, panoptes_workflow, display_name, priority, session
            )

        assign_panoptes_workflow_to_panoptes_subject_set(panoptes_workflow, panoptes_subject_set)

    session.commit()

    return list(
        session.query(LocalSubjectSet)
        .filter(LocalSubjectSet.zooniverse_workflow_id == panoptes_workflow_id)
        .filter(LocalSubjectSet.priority.in_(range(1, num_sets + 1)))
    )


# Public functions -------------------------------------------------------------
def get_priority_panoptes_subject_sets(
    panoptes_project_id: str | int, panoptes_workflow_id: str | int, num_priority_subject_sets: int
) -> List[PanoptesSubjectSet]:
    """
    Return a list of Panoptes SubjectSets which are used for priority/confidence
    binning.

    This function queries the database for subject sets which have a priority which
    fit into the `num_priority_sets` variable. `num_priority_sets` controls how many priority sets
    to get, which will in turn affect the binning.

    New subject sets will be created for any missing, e.g. if the number of sets
    goes from 4 to 5 or if any subject sets are deleted on the online interface.
    Subject sets are not deleted/removed from the workflow if the number of
    subject set shrinks. This shouldn't matter as no subjects will be binned
    into them anyway.

    This function also updates the local subject set table.

    Parameters
    ----------
    panoptes_project_id : str | int
        The Zooniverse ID of the project containing the subject sets.
    panoptes_workflow_id : str | int
        The Zooniverse ID of the workflow the subject sets will be associated
        with.
    num_priority_subject_sets : int, optional
        The number of priority subject sets to get.

    Returns
    -------
    List[PanoptesSubjectSet]
        A priority sorted list of the priority subject sets, as Panoptes
        SubjectSet objects.
    """
    requested_priorities: List[int] = list(range(1, num_priority_subject_sets + 1))
    panoptes_subject_sets: List[PanoptesSubjectSet] = PanoptesSubjectSet.where(
        project_id=config["ZOONIVERSE"]["project_id"]
    )

    with Session(
        engine := connect_to_database_engine(config_paths["database"]),
        info={"url": engine.url},
    ) as session:
        sync_local_subject_set_database_with_zooniverse(
            session, panoptes_subject_sets, panoptes_subject_sets.meta["count"]
        )

        local_subject_sets_already_in_workflow: List[LocalSubjectSet] = (
            session.query(LocalSubjectSet)
            .filter(LocalSubjectSet.zooniverse_workflow_id == int(panoptes_workflow_id))
            .filter(LocalSubjectSet.priority.in_(requested_priorities))
        )

        # need a list of priorities to check that what we have makes sense
        # and to know what priorities we are missing.
        # We need to ensure there are no missing digits, e.g. if priorities =
        # [1, 3, 4], is_sequential will be False. But will be true if
        # priorities = [1, 3, 2] or some combination like that
        priorities_in_database: List[int] = [
            subject_set.priority for subject_set in local_subject_sets_already_in_workflow
        ]

        if priorities_in_database:
            sequential_priorities: List[int] | None = sorted(priorities_in_database) == list(
                range(min(priorities_in_database), max(priorities_in_database) + 1)
            )
        else:
            sequential_priorities: List[int] | None = False

        if len(priorities_in_database) != num_priority_subject_sets or sequential_priorities is False:
            local_subject_sets_already_in_workflow: List[LocalSubjectSet] = (
                __create_missing_priority_local_subject_sets(
                    session,
                    panoptes_project_id,
                    panoptes_workflow_id,
                    num_priority_subject_sets,
                    priorities_in_database,
                )
            )

    # return a list of SubjectSets sorted by priority
    return [
        PanoptesSubjectSet.find(local_subject_set.zooniverse_subject_set_id)
        for local_subject_set in sorted(list(local_subject_sets_already_in_workflow), key=lambda x: x.priority)
    ]


def set_priority_subject_set_weights_for_workflow(
    panoptes_subject_set_ids: Iterable[str | int],
    weights_to_assign: Iterable[float],
    panoptes_workflow: PanoptesWorkflow,
) -> None:
    """
    Set the priority weights for subject sets in a workflow.

    The weights of the subject set modify the selection behaviour. If there are
    3 subject sets with weights [0.9, 0.05, 0.05] then for 10 subjects we
    should expect 9 subjects from the first subject set and 2 from the other.
    The weights must sum up to 1.

    Parameters
    ----------
    panoptes_subject_set_ids : Iterable[str | int]
        A list of Zooniverse subject set IDs to modify the selection weighting for.
    weights_to_assign: Iterable[float]
        A list of selection weights, in the same order as the subject IDs.
    panoptes_workflow : PanoptesWorkflow
        The workflow to assign the selection weighting to.
    """
    if not math.isclose(sum(weights_to_assign), 1.0):
        raise ValueError(f"Selection weighting for subject sets does not sum to 1, but to {sum(weights_to_assign)}")

    if len(weights_to_assign) != len(panoptes_subject_set_ids):
        raise ValueError(
            # pylint: disable=line-too-long
            f"Mismatch in length between subject set ids ({len(panoptes_subject_set_ids)}) and selection weights ({len(weights_to_assign)})"
        )

    with Session(
        engine := connect_to_database_engine(config_paths["database"]),
        info={"url": engine.url},
    ) as session:
        for panoptes_subject_set_id, weight in zip(panoptes_subject_set_ids, weights_to_assign):
            local_subject_set: LocalSubjectSet = (
                session.query(LocalSubjectSet)
                .filter(LocalSubjectSet.zooniverse_subject_set_id == int(panoptes_subject_set_id))
                .filter(LocalSubjectSet.zooniverse_workflow_id == int(panoptes_workflow.id))
                .first()
            )
            if not local_subject_set:
                raise ValueError(
                    f"Attempting to assign a weight to subject set {panoptes_subject_set_id} not part of workflow {panoptes_workflow.id}"
                )
            local_subject_set.weight = weight

    panoptes_workflow.reload()  # the API would sometimes fail if we don't do a reload
    panoptes_workflow.configuration["subject_set_weights"] = dict(zip(panoptes_subject_set_ids, weights_to_assign))
    panoptes_workflow.save()


def bin_subjects_into_priority_panoptes_subject_sets(
    priority_panoptes_subject_sets: List[PanoptesSubjectSet],
    panoptes_workflow_id: str | int,
    commit_frequency: int = 250,
) -> None:
    """
    Arrange subjects into priority subject sets depending on machine
    confidence.

    Subjects are binned into "priority subject sets" by the machine confidence
    of the stamps which they represent. The number of these subject sets can be
    changed dynamically with the `num_priority_sets` variable. This will change
    the binning, but will not modify the subjects sets which exist on
    Zooniverse.

    Parameters
    ----------
    priority_panoptes_subject_sets : List[SubjectSet]
        A list of subject sets which subjects will be binned into by confidence.
    panoptes_workflow_id : int
        The workflow where subjects are being binned into.
    commit_frequency : int, optional
        The frequency of which to save changes, by default 250 subjects.
    """
    num_priority_sets: int = len(priority_panoptes_subject_sets)
    priority_bin_width: float = 1 / num_priority_sets

    with Session(
        engine := connect_to_database_engine(config_paths["database"]),
        info={"url": engine.url},
    ) as session:
        local_subjects: Query[LocalSubject] = session.query(LocalSubject).filter(LocalSubject.retired == 0)
        num_local_subjects: int = local_subjects.count()
        for i, local_subject in enumerate(
            tqdm(
                local_subjects,
                total=num_local_subjects,
                desc="Arranging subjects into subject sets",
                unit="subject",
                leave=logger.level <= logging.INFO,
                disable=logger.level > logging.INFO,
            )
        ):
            confidence: float = local_subject.sonification.machine_confidence

            # if the confidence is null, then we'll just shove that into the
            # highest priority subject set to try and expedite getting rid of it
            if not confidence:
                confidence: float = 0

            # bin by confidence into a priority subject set, where confidence is
            # between 0 and 1
            priority: int = int(max(min(confidence // priority_bin_width, num_priority_sets), 0))

            # when the machine confidence changes into a different priority bin,
            # the subject has to be removed from the old subject set and moved
            # into the new one
            if (
                local_subject.zooniverse_subject_set_id
                and local_subject.zooniverse_subject_set_id != priority_panoptes_subject_sets[priority].id
            ):
                try:
                    # disabling the following warning, because the code works as expected
                    # pylint: disable=cell-var-from-loop
                    old_panoptes_subject_set: PanoptesSubjectSet = next(
                        filter(
                            lambda x: x.id == local_subject.zooniverse_subject_set_id, priority_panoptes_subject_sets
                        )
                    )
                except StopIteration:
                    old_panoptes_subject_set: PanoptesSubjectSet = PanoptesSubjectSet.find(
                        local_subject.zooniverse_subject_set_id
                    )
                    priority_panoptes_subject_sets.append(old_panoptes_subject_set)

                # if the subject is new (i.e. never been in a subject set
                # before) or not in a subject set, then we obviously can't
                # remove it from an old subject set
                if old_panoptes_subject_set:
                    panoptes_subject: PanoptesSubject = PanoptesSubject.find(local_subject.zooniverse_subject_id)
                    old_panoptes_subject_set.remove(panoptes_subject)

                priority_panoptes_subject_sets[priority].input(panoptes_subject)
                local_subject.zooniverse_subject_set_id = priority_panoptes_subject_sets[priority].id
                local_subject.zooniverse_workflow_id = panoptes_workflow_id

            if (i + 1) % commit_frequency == 0:
                __binning_checkpoint(priority_panoptes_subject_sets, session)
                logger.debug(
                    f"Processed {i + 1}/{num_local_subjects} ({100 * (i + 1) / num_local_subjects:.0f}) subjects",
                )
        __binning_checkpoint(priority_panoptes_subject_sets, session)
        logger.debug(f"Processed {num_local_subjects}/{num_local_subjects} (100%%) subjects")


def unlink_unused_subject_sets_from_workflow(panoptes_workflow: PanoptesWorkflow, num_priority_sets: int) -> None:
    """
    Unlink priority subject sets which are not used in a workflow.

    This function will remove priority subject sets which have been
    "dynamically" removed from the workflow due to a shrinking number of
    priority sets. The entry in MoleDB is also updated.

    Changes seem to take a bit of time to become active in the online UI.

    Parameters
    ----------
    panoptes_workflow : PanoptesWorkflow
        A Workflow object for the workflow to be updated.
    num_priority_sets : int
        The number of priority subject sets in the workflow.
    """
    panoptes_workflow.reload()
    with Session(
        engine := connect_to_database_engine(config["PATHS"]["database"]),
        info={"url": engine.url},
    ) as session:
        local_subject_sets_to_remove: Query[LocalSubjectSet] = (
            session.query(LocalSubjectSet)
            .filter(LocalSubjectSet.zooniverse_workflow_id == panoptes_workflow.id)
            .filter(  # subject sets which are not in the "priority range" are have a NULL priority
                or_(
                    LocalSubjectSet.priority.not_in(range(1, num_priority_sets + 1)),
                    LocalSubjectSet.priority is None,  # pylint: disable=singleton-comparison
                )
            )
        )

        if logger.level == logging.DEBUG:
            set_names: str = ",".join([set.display_name for set in local_subject_sets_to_remove])
            logger.debug("Unlinking the following subject sets from workflow %s: %s", panoptes_workflow.id, set_names)

        # this is updating the subject set entries in the database
        panoptes_subject_sets: List[PanoptesSubjectSet] = []
        for local_subject_set in local_subject_sets_to_remove:
            panoptes_subject_sets.append(PanoptesSubjectSet.find(local_subject_set.zooniverse_subject_set_id))
            local_subject_set.zooniverse_workflow_id = None

        session.commit()

        panoptes_workflow.remove_subject_sets(panoptes_subject_sets)
        panoptes_workflow.save()


def update_weighted_sampling_scheme(
    panoptes_project_id: str | int = config["ZOONIVERSE"]["project_id"],
    panoptes_workflow_id: str | int = config["ZOONIVERSE"]["workflow_id"],
) -> None:
    """
    Update the subjects in the subject sets given the machine confidence
    for sonifications.

    This function will,

        1) Create a number of "priority subject sets" which are subjects set
           which contain subjects/stamps in a certain confidence interval
        2) Bin subjects by their confidence into the priority subject sets.
        3) Set the sampling weighting for the priority subject sets.
        4) Unlinks any unused subject sets from the workflow

    These features are controlled by parameters in the configuration file.
    Subjects can will only exist in one subject set at once.

    Parameters
    ----------
    panoptes_project_id : str | int
        The Zooniverse ID of the project containing the subject sets. By default
        this is the values in the configuration file.
    panoptes_workflow_id : str | int
        The Zooniverse ID of the workflow containing the subject sets being
        updated. By default, this is the value in the configuration file.
    """
    panoptes_workflow: PanoptesWorkflow = get_panoptes_workflow(config["ZOONIVERSE"]["workflow_id"])
    num_priority_sets: int = int(config["ACTIVE LEARNING"]["num_priority_sets"])

    # the weights should be written as a comma separated list, which we need to
    # eval as a tuple
    try:
        selection_weights: List[float] = list(ast.literal_eval(config["ACTIVE LEARNING"]["selection_weighting"]))
    except SyntaxError as exc:
        raise SyntaxError(
            "selection-weighting in the configuration file is not correctly formatted, should be a comma separated list"
        ) from exc

    priority_subject_sets: List[PanoptesSubjectSet] = get_priority_panoptes_subject_sets(
        panoptes_project_id, panoptes_workflow_id, num_priority_sets
    )
    bin_subjects_into_priority_panoptes_subject_sets(copy.copy(priority_subject_sets), panoptes_workflow.id)
    set_priority_subject_set_weights_for_workflow(
        [subject_set.id for subject_set in priority_subject_sets], selection_weights, panoptes_workflow
    )
    unlink_unused_subject_sets_from_workflow(panoptes_workflow, num_priority_sets)
