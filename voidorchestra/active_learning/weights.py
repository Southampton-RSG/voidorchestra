# !/usr/bin/env python3
# -*- coding: utf-8 -*-

"""The weight module handles assigning weights to subjects and to subject sets.
The weights are used to alter the probability of a subject or subject from a
subject set being shown to a user.
"""

from __future__ import annotations

import ast
import copy
import logging
import math
from typing import List, Iterable

from panoptes_client import SubjectSet
from panoptes_client import Project
from panoptes_client import Subject
from panoptes_client import Workflow
from sqlalchemy import or_
from sqlalchemy.orm import Session
from tqdm import tqdm

import voidorchestra.db
import molemarshal
import molemarshal.log
from molemarshal.zooniverse import workflows
from molemarshal.zooniverse import sync


logger = molemarshal.log.get_logger(__name__.replace(".", "-"))


# Private functions ------------------------------------------------------------


def __create_new_subject_set(
    project: Project, workflow: Workflow, display_name: str, priority: int, session: Session
) -> None:
    """Create a new subject set on Zooniverse.

    Creates a new subject set with the given name on Zooniverse, and creates a
    new entry in the MoleMarshal database. This is why there are some seemingly
    redundant arguments.

    Parameters
    ----------
    project : Project
        A Project class for the project the subject set will be linked to.
    workflow : Workflow
        A Workflow class for the workflow the subject set will be part of, or
        linked to.
    display_name : str
        The name of the new subject set.
    priority : int
        The priority ranking of the subject set.
    session : Session
        The database session to add the new subject set to.
    """
    subject_set = SubjectSet()
    subject_set.links.project = project
    subject_set.display_name = display_name
    subject_set.save()

    session.add(
        voidorchestra.db.SubjectSet(
            subject_set_id=int(subject_set.id),
            priority=int(priority),
            project_id=int(project.id),
            workflow_id=int(workflow.id),
            display_name=subject_set.display_name,
        )
    )

    return subject_set


def __binning_checkpoint(subject_sets_to_update: List[SubjectSet], session: Session) -> None:
    """Save changes to subject sets and the database session.

    Parameters
    ----------
    subject_sets_to_update : List[SubjectSet]
        The subject sets to save changes to.
    session : Session
        The session to commit changes to.
    """
    for subject_set in subject_sets_to_update:
        subject_set.save()
    session.commit()


def __create_missing_priority_subject_sets(
    session: Session, project_id: str | int, workflow_id: str | int, num_sets: int, priorities: List[int] | None = None
) -> List[voidorchestra.db.SubjectSet]:
    """Create new or find a subject set for the given priorities.

    Only the missing priority subject sets will be created or attempted to be
    found. This is done by figuring out the priority rankings which are missing.
    Newly created subject sets are added to the MoleMarshal database.

    Parameters
    ----------
    session : Session
        A ORM session to MoleDB.
    project_id : str | int
        The Zooniverse ID of the project subject sets will belong to.
    workflow_id : str | int
        The Zooniverse ID of the workflow the subject sets will be assigned to.
    num_sets : int
        The number of subject sets which should exist.
    priorities : List[int] | None
        The requested priorities of the subject sets. The default value of None
        will create subject sets from range(1 num_sets + 1).

    Returns
    -------
    List[SubjectSet]
        A list of Panoptes SubjectSet objects of the created/retrieved subject
        sets.
    """
    project = Project.find(project_id)
    workflow = workflows.get_workflow(workflow_id)

    # If priorities is not provided, then create a new collection of priority
    # subject sets. If it is provided, then we need to figure out which
    # priorities are missing using set().difference() on range(1, num_sets+1)
    if priorities:
        new_priorities_to_create = set(range(1, num_sets + 1)).difference(priorities)
    else:
        new_priorities_to_create = range(1, num_sets + 1)

    for priority in new_priorities_to_create:
        display_name = f"WF{workflow.id} Mole Stamp Priority #{priority}"

        # going to double check first that we def don't have a subject set which
        # already fulfills the purpose
        existing_sets = (
            session.query(voidorchestra.db.SubjectSet)
            .filter(voidorchestra.db.SubjectSet.priority == int(priority))
            .filter(
                # pylint: disable=singleton-comparison
                or_(voidorchestra.db.SubjectSet.workflow_id == int(workflow.id), voidorchestra.db.SubjectSet.workflow_id == None)
            )
        )
        num_existing = existing_sets.count()

        if num_existing:
            logger.debug("A subject set already exists with priority %d for workflow %s", priority, workflow.id)
            for _iter in existing_sets:
                if _iter.workflow_id == None:  # pylint: disable=singleton-comparison
                    index = [subject_set.display_name for subject_set in project.links.subject_sets].index(display_name)
                    subject_set = project.links.subject_sets[index]
                    _iter.workflow_id = int(workflow.id)
            # this is purely a safety mechanism in-case the subject set is
            # somehow not found in the project, so we will create it
            if not subject_set:
                subject_set = __create_new_subject_set(project, workflow, display_name, priority, session)
        else:
            subject_set = __create_new_subject_set(project, workflow, display_name, priority, session)

        workflows.assign_workflow_to_subject_set(workflow, subject_set)

    session.commit()

    return list(
        session.query(voidorchestra.db.SubjectSet)
        .filter(voidorchestra.db.SubjectSet.workflow_id == workflow_id)
        .filter(voidorchestra.db.SubjectSet.priority.in_(range(1, num_sets + 1)))
    )


# Public functions -------------------------------------------------------------


def get_priority_subject_sets(project_id: str | int, workflow_id: str | int, num_sets: int) -> List[SubjectSet]:
    """Return a list of SubjectSets which are used for priority/confidence
    binning.

    This function queries MoleDB for subject sets which have a priority which
    fit into the `num_sets` variable. `num_sets` controls how many priority sets
    to get, which will in turn affect the binning.

    New subject sets will be created for any missing, e.g. if the number of sets
    goes from 4 to 5 or if any subject sets are deleted on the online interface.
    Subject sets are not deleted/removed from the workflow if the number of
    subject set shrinks. This shouldn't matter as no subjects will be binned
    into them anyway.

    This function also updates the MoleDB subject set table.

    Parameters
    ----------
    project_id : str | int
        The Zooniverse ID of the project containing the subject sets.
    workflow_id : str | int
        The Zooniverse ID of the workflow the subject sets will be associated
        with.
    num_sets : int, optional
        The number of priority subject sets to get.

    Returns
    -------
    List[SubjectSet]
        A priority sorted list of the priority subject sets, as Panoptes
        SubjectSet objects.
    """
    requested_priorities = list(range(1, num_sets + 1))
    zooniverse_subject_sets = SubjectSet.where(project_id=voidorchestra.config["ZOONIVERSE"]["project_id"])

    with Session(voidorchestra.db.connect_to_database_engine(voidorchestra.config["PATHS"]["database"])) as session:
        sync.sync_subject_set_database_with_zooniverse(
            session, zooniverse_subject_sets, zooniverse_subject_sets.meta["count"]
        )

        subject_sets_already_in_workflow = (
            session.query(voidorchestra.db.SubjectSet)
            .filter(voidorchestra.db.SubjectSet.workflow_id == int(workflow_id))
            .filter(voidorchestra.db.SubjectSet.priority.in_(requested_priorities))
        )

        # need a list of priorities to check that what we have makes sense
        # and to know what priorities we are missing.
        # We need to ensure there are no missing digits, e.g. if priorities =
        # [1, 3, 4], is_sequential will be False. But will be true if
        # priorities = [1, 3, 2] or some combination like that
        priorities_in_database = [subject_set.priority for subject_set in subject_sets_already_in_workflow]

        if priorities_in_database:
            sequential_priorities = sorted(priorities_in_database) == list(
                range(min(priorities_in_database), max(priorities_in_database) + 1)
            )
        else:
            sequential_priorities = False

        if len(priorities_in_database) != num_sets or sequential_priorities is False:
            subject_sets_already_in_workflow = __create_missing_priority_subject_sets(
                session, project_id, workflow_id, num_sets, priorities_in_database
            )

    # return a list of SubjectSets sorted by priority
    return [
        SubjectSet.find(subject_set.subject_set_id)
        for subject_set in sorted(list(subject_sets_already_in_workflow), key=lambda x: x.priority)
    ]


def set_priority_subject_set_weights_for_workflow(
    subject_set_ids: Iterable[str | int], weights_to_assign: Iterable[float], workflow: Workflow
) -> None:
    """Set the priority weights for subject sets in a workflow.

    The weights of the subject set modify the selection behaviour. If there are
    3 subject sets with weights [0.9, 0.05, 0.05] then for 10 subjects we
    should expect 9 subjects from the first subject set and 2 from the other.
    The weights must sum up to 1.

    Parameters
    ----------
    subject_set_ids : Iterable[str  |  int]
        A list of subject set IDs to modify the selection weighting for.
    weights_to_assign: Iterable[float]
        A list of selection weights, in the same order as the subject IDs.
    workflow : Workflow
        The workflow to assign the selection weighting to.
    """
    if not math.isclose(sum(weights_to_assign), 1.0):
        raise ValueError(f"Selection weighting for subject sets does not sum to 1, but to {sum(weights_to_assign)}")

    if len(weights_to_assign) != len(subject_set_ids):
        raise ValueError(
            # pylint: disable=line-too-long
            f"Mismatch in length between subject set ids ({len(subject_set_ids)}) and selection weights ({len(weights_to_assign)})"
        )

    with Session(voidorchestra.db.connect_to_database_engine(voidorchestra.config["PATHS"]["database"])) as session:
        for subject_set_id, weight in zip(subject_set_ids, weights_to_assign):
            subject_set = (
                session.query(voidorchestra.db.SubjectSet)
                .filter(voidorchestra.db.SubjectSet.subject_set_id == int(subject_set_id))
                .filter(voidorchestra.db.SubjectSet.workflow_id == int(workflow.id))
                .first()
            )
            if not subject_set:
                raise ValueError(
                    f"Attempting to assign a weight to subject set {subject_set_id} not part of workflow {workflow.id}"
                )
            subject_set.weight = weight

    workflow.reload()  # the API would sometimes fail if we don't do a reload
    workflow.configuration["subject_set_weights"] = dict(zip(subject_set_ids, weights_to_assign))
    workflow.save()


def bin_subjects_into_priority_subject_sets(
    priority_subject_sets: List[SubjectSet],
    workflow_id: str | int,
    commit_frequency: int = 250,
) -> None:
    """Arrange subjects into priority subject sets depending on machine
    confidence.

    Subjects are binned into "priority subject sets" by the machine confidence
    of the stamps which they represent. The number of these subject sets can be
    changed dynamically with the `num_priority_sets` variable. This will change
    the binning, but will not modify the subjects sets which exist on
    Zooniverse.

    Parameters
    ----------
    priority_subject_sets : List[SubjectSet]
        A list of subject sets which subjects will be binned into by confidence.
    workflow_id : int
        The workflow where subjects are being binned into.
    commit_frequency : int, optional
        The frequency of which to save changes, by default 250 subjects.
    """
    num_priority_sets = len(priority_subject_sets)
    priority_bin_width = 1 / num_priority_sets

    with Session(voidorchestra.db.connect_to_database_engine(voidorchestra.config["PATHS"]["database"])) as session:
        subjects = session.query(voidorchestra.db.subject.Subject).filter(voidorchestra.db.Subject.retired == 0)
        num_subjects = subjects.count()
        for i, subject in enumerate(
            tqdm(
                subjects,
                total=num_subjects,
                desc="Arranging subjects into subject sets",
                unit="subject",
                leave=logger.level <= logging.INFO,
                disable=logger.level > logging.INFO,
            )
        ):
            confidence = subject.stamp.machine_confidence

            # if the confidence is null, then we'll just shove that into the
            # highest priority subject set to try and expedite getting rid of it
            if not confidence:
                confidence = 0

            # bin by confidence into a priority subject set, where confidence is
            # between 0 and 1
            priority = int(max(min(confidence // priority_bin_width, num_priority_sets), 0))

            # when the machine confidence changes into a different priority bin,
            # the subject has to be removed from the old subject set and moved
            # into the new one
            if subject.subject_set_id and subject.subject_set_id != priority_subject_sets[priority].id:
                try:
                    # disabling the following warning, because the code works as expected
                    # pylint: disable=cell-var-from-loop
                    old_subject_set = next(filter(lambda x: x.id == subject.subject_set_id, priority_subject_sets))
                except StopIteration:
                    old_subject_set = SubjectSet.find(subject.subject_set_id)
                    priority_subject_sets.append(old_subject_set)

                # if the subject is new (i.e. never been in a subject set
                # before) or not in a subject set, then we obviously can't
                # remove it from an old subject set
                if old_subject_set:
                    subject_zoo = Subject.find(subject.subject_id)
                    old_subject_set.remove(subject_zoo)

                priority_subject_sets[priority].add(subject_zoo)
                subject.subject_set_id = priority_subject_sets[priority].id
                subject.workflow_id = workflow_id

            if (i + 1) % commit_frequency == 0:
                __binning_checkpoint(priority_subject_sets, session)
                logger.debug("Processed %d/%d (%.0f%%) subjects", i + 1, num_subjects, (i + 1) / num_subjects * 100)

        __binning_checkpoint(priority_subject_sets, session)
        logger.debug("Processed %d/%d (100%%) subjects", num_subjects, num_subjects)


def unlink_unused_subject_sets_from_workflow(workflow: Workflow, num_priority_sets: int) -> None:
    """Unlink priority subject sets which are not used in a workflow.

    This function will remove priority subject sets which have been
    "dynamically" removed from the workflow due to a shrinking number of
    priority sets. The entry in MoleDB is also updated.

    Changes seem to take a bit of time to become active in the online UI.

    Parameters
    ----------
    workflow : Workflow
        A Workflow object for the workflow to be updated.
    num_priority_sets : int
        The number of priority subject sets in the workflow.
    """
    workflow.reload()
    with Session(voidorchestra.db.connect_to_database_engine(voidorchestra.config["PATHS"]["database"])) as session:
        db_subject_sets_to_remove = (
            session.query(voidorchestra.db.SubjectSet)
            .filter(voidorchestra.db.SubjectSet.workflow_id == workflow.id)
            .filter(  # subject sets which are not in the "priority range" are have a NULL priority
                or_(
                    voidorchestra.db.SubjectSet.priority.not_in(range(1, num_priority_sets + 1)),
                    voidorchestra.db.SubjectSet.priority == None,  # pylint: disable=singleton-comparison
                )
            )
        )

        if logger.level == logging.DEBUG:
            set_names = ",".join([set.display_name for set in db_subject_sets_to_remove])
            logger.debug("Unlinking the following subject sets from workflow %s: %s", workflow.id, set_names)

        # this is updating the subject set entries in the database
        zoo_subject_sets = []
        for db_subject_set in db_subject_sets_to_remove:
            zoo_subject_sets.append(SubjectSet.find(db_subject_set.subject_set_id))
            db_subject_set.workflow_id = None

        session.commit()

        workflow.remove_subject_sets(zoo_subject_sets)
        workflow.save()


def update_weighted_sampling_scheme(
    project_id: str | int = voidorchestra.config["ZOONIVERSE"]["project_id"],
    workflow_id: str | int = voidorchestra.config["ZOONIVERSE"]["workflow_id"],
) -> None:
    """Update the subjects in the subject sets given the machine confidence
    for stamps.

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
    project_id : str | int
        The Zooniverse ID of the project containing the subject sets. By default
        this is the values in the configuration file.
    workflow_id : str | int
        The Zooniverse ID of the workflow containing the subject sets being
        updated. By default this is the value in the configuration file.
    """
    workflow = workflows.get_workflow(voidorchestra.config["ZOONIVERSE"]["workflow_id"])
    num_priority_sets = int(voidorchestra.config["ACTIVE LEARNING"]["num_priority_sets"])

    # the weights should be written as a comma separated list, which we need to
    # eval as a tuple
    try:
        selection_weights = list(ast.literal_eval(voidorchestra.config["ACTIVE LEARNING"]["selection_weighting"]))
    except SyntaxError as exc:
        raise SyntaxError(
            "selection-weighting in the configuration file is not correctly formatted, should be a comma separated list"
        ) from exc

    priority_subject_sets = get_priority_subject_sets(project_id, workflow_id, num_priority_sets)
    bin_subjects_into_priority_subject_sets(copy.copy(priority_subject_sets), workflow.id)
    set_priority_subject_set_weights_for_workflow(
        [subject_set.id for subject_set in priority_subject_sets], selection_weights, workflow
    )
    unlink_unused_subject_sets_from_workflow(workflow, num_priority_sets)
