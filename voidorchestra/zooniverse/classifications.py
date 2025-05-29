#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
The classifications module deals with downloading and assigning workflow
classifications to subjects and stamp images. There are two main functions in
this module

- :meth:`get_workflow_classifications`,
- :meth:`update_classification_database`.

which handle downloading classifications and matching those classifications to
subjects and therefore stamps, respectively.
"""

from __future__ import annotations

import logging
from typing import Any
from typing import List

import voidorchestra
import voidorchestra.db.classification
import voidorchestra.db.subject
from panoptes_client import Caesar
from panoptes_client import Subject
from panoptes_client import Workflow
from panoptes_client.panoptes import PanoptesAPIException
from sqlalchemy.orm import Session
from tqdm import tqdm

import voidorchestra
import voidorchestra.log

logger: logging.Logger = voidorchestra.log.get_logger(__name__.replace(".", "-"))


# Private functions ------------------------------------------------------------


def __dump_classifications_to_file(classifications: list[dict[str, int]], workflow_name: str) -> None:
    """Write a list of classifications to a CSV file.

    This function is meant to  be used with the output from
    :meth:`download_classifications_for_workflow_reducer`.

    Parameters
    ----------
    classifications: List[dict]
        A list of dicts containing information about the classifications.
        Expects the keys "id", "subject_id" and "answer_index".
    workflow_name: str
        The name of the workflow where classifications are coming from.
    """
    # remove special characters from name (excluding spaces and _) and format
    # what's left to fit form: workflow_name_classification.csv
    workflow_name = (
        workflow_name.translate(str.maketrans("", "", "!\"#$%&'()*+,-./:;<=>?@[\\]^`{|}~")).lower().replace(" ", "_")
    )

    with open(
        file_name := f"{voidorchestra.config['PATHS']['data_directory']}/{workflow_name}_classifications.csv",
        "w",
        encoding="utf-8",
    ) as file_out:
        file_out.write("classification_id,subject_id,classification,reducer\n")
        for classification in classifications:
            file_out.write(f"{classification['classification_id']},{classification['subject_id']},")
            file_out.write(f"{classification['answer_index']},{classification['reducer_key']}\n")

    logger.debug("Classifications for %s dumped to file %s", workflow_name, file_name)


def __convert_answer_to_bool(answer: str) -> str | bool:
    """Convert an answer to something appropriate for the database.

    An answer of "yes" or "no" will be converted to True or False. If the answer
    string is something other than "yes" or "no", then the answer string is
    returned.

    Parameters
    ----------
    answer: str
        The answer to potentially convert to a bool.

    Returns
    -------
    conversion: str | bool
        If the input answer is some combination of "yes" or "no", then True or
        False is returned. Otherwise the input answer is returned.
    """
    answer = str(answer)
    lower = answer.lower()
    # pylint: disable=simplifiable-if-expression
    return (
        answer if lower not in ["yes", "no", "true", "false"] else True if lower in ["yes", "true"] else False
    )  # heck yeah, nested ternary


# Public functions -------------------------------------------------------------


def convert_answer_index_to_value(reducer_key: str, answer_index: dict, task_answers: dict) -> Any | None:
    """Get the classification value for a subject for a specific reducer.

    The reducer output from Caesar only outputs the "answer_index" which is just
    a number. In most cases we want to know what the answer actually is, and
    then to convert that into the required data format for the database.
    To do this we use the task answers dictionary/list to convert answer_index
    into the actual value of the consensus answer/classification. The function
    :meth:`__convert_reducer_key_to_task_number` is used to index into the
    correct task answers in the `task_answers` dictionary given the
    reducer key. Yes/No answers are also converted to True/False using
    :meth:`__convert_answer_to_bool`.

    Parameters
    ----------
    reducer_key : str
        The reducer key to get the classification from.
    answer_index : int
        The classification index, as from tha Caesar reducer or from the
        MoleMarshal database.
    task_answers : dict
        A dictionary of task answers to convert the "answer_index" into. This
        should be the dict returned from :meth:`get_workflow_task_answers`.

    Returns
    -------
    Any | None
        The classification in terms of the answers given. If there is no
        reducer output then None is returned instead.
    """
    if reducer_key not in voidorchestra.config["REDUCERS"]:
        raise ValueError(f"{reducer_key} not in the REDUCERS section of configuration file")

    return __convert_answer_to_bool(task_answers[voidorchestra.config["REDUCERS"][reducer_key]][answer_index])


def get_workflow_task_answers(workflow: Workflow) -> dict:
    """Return a dictionary of answer keys for a workflow task.

    From the Caesar documentation, the extractor we use "retrieves the index of
    the answer from the classification. Indices are C-style, i.e. the first
    index is "0".". This basically means the extracted (and reduced) data is
    going to be a number which relates to the position of the answers in the
    list from workflow["tasks"]["TX"]["answers"]. The string representation of
    that answer is then a key named "label".

    The point of this function is to simply act as a convenience to get the task
    answers easier.

    Parameters
    ----------
    workflow: Workflow
        The workflow to get the task answers from.

    Returns
    -------
    dict
        A dictionary containing the answers in task workflows, looking like

        .. code::

            {
                "T0": ["Yes", "No"],
                "T1": ["1", "2", "3", "4", "5"]
            }
    """
    return {
        task_key: [str(answer["label"]) for answer in workflow.tasks[task_key]["answers"]]
        for task_key in workflow.tasks.keys()
    }


def get_workflow_classifications(session: Session, workflow_id: str | int) -> List[dict]:
    """Retrieve the classifications for all subjects in a workflow.

    This will retrieve all the classifications for the subjects assigned to the
    given workflow. This function is intended to get the data from a Caesar
    reducer.

    When debug logging is enabled, then classifications which have been
    retrieved are dumped into a CSV file by
    :meth:`__dump_classifications_to_file`.

    Parameters
    ----------
    session: Session
        A database session to query subjects from.
    caesar: Caesar
        A Caesar instance used to get data about the workflows Caesar reducers.
    workflow_id: str | int | None
        The ID of the Zooniverse workflow to download classifications from.

    Returns
    -------
    classifications: List[dict]
        A list containing a dict with keys "classification_id", "subject_id",
        "answer_index". Each dict is a classification for a subject.

        .. code::

            classifications = [
                "classification_id": ...,
                "subject_id": ...,
                "answer_index": ...,
                "reducer_key": ...,
            ]
    """
    try:
        workflow = Workflow.find(workflow_id)
    except PanoptesAPIException as exc:
        raise ValueError(f"Unable to open workflow with id {workflow_id}") from exc

    caesar = Caesar()
    reducers_in_workflow = caesar.get_workflow_reducers(workflow.id)
    if not reducers_in_workflow:
        raise ValueError(f"There are no Caesar reducers in workflow {workflow.id}")
    workflow_reducer_keys = [reducer["key"] for reducer in reducers_in_workflow]

    subjects = session.query(voidorchestra.db.Subject).filter(voidorchestra.db.Subject.workflow_id == workflow.id)

    if subjects.count() == 0:
        raise ValueError(f"There are no subjects in the database linked to workflow {workflow.id}.")

    classifications = []

    for subject in tqdm(
        subjects,
        "Retrieving subject classifications",
        total=subjects.count(),
        unit="subjects",
        leave=logger.level <= logging.INFO,
        disable=logger.level > logging.INFO,
    ):
        # use filter to get the dictionaries for just the active reducers. the
        # caesar function below returns a list of dictionaries
        reducer_outputs = list(
            filter(
                lambda reducer: reducer["reducer_key"] in workflow_reducer_keys,
                caesar.get_reductions_by_workflow_and_subject(workflow.id, subject.subject_id),
            )
        )

        # don't need all the info from the reducer, so compress to 4 key
        # values. Also we can weed out incorrect nonsense which sometimes creeps
        # into the consensus reducer output
        for output in reducer_outputs:
            try:
                classifications.append(
                    {
                        "classification_id": output["id"],
                        "subject_id": output["subject_id"],
                        "answer_index": int(output["data"].get("most_likely", None)),
                        "reducer_key": output["reducer_key"],
                    }
                )
            except (ValueError, TypeError):
                logger.debug(
                    "Classification %d has a bad classification value of %s",
                    output["id"],
                    output["data"].get("most_likely", None),
                )
                continue

    if logger.level == logging.DEBUG:
        __dump_classifications_to_file(classifications, workflow.display_name)

    return classifications


def process_workflow_classifications(
    session: Session, reduced_data: List[dict], workflow_id: str | int, commit_frequency: int = 250
) -> int:
    """Process classifications for all subject classifications.

    This function iterates over the provided reduced data and matches
    classifications to subjects. If a subject is not in the database or not
    assigned to a subject set, then the classification is not recorded.

    Parameters
    ----------
    session : Session
        The database session to write to.

    reduced_data : List[dict]
        A list of consensus reductions for subjects.
    commit_frequency : int
        The frequency of which to commit to the database.
    workflow_id : str | int
        The ID of the workflow the classifications are coming from, by default
        None.

    Returns
    -------
    int
        The number of classifications successfully linked to a subject.
    """
    num_subjects_linked = 0
    num_classifications = len(reduced_data)

    for i, subject_classification in enumerate(
        tqdm(
            reduced_data,
            "Adding classifications to MoleDB",
            unit="classification",
            leave=logger.level <= logging.INFO,
            disable=logger.level > logging.INFO,
        )
    ):
        # sometimes the reducers will throw in random junk which are no longer
        # subjects tracked, or for subjects which are in the project but not
        # linked to a subject set. filter these out with a debug warning
        subject = (
            session.query(voidorchestra.db.Subject)
            .filter(voidorchestra.db.Subject.subject_id == subject_classification["subject_id"])
            .first()
        )
        if not subject:
            logger.debug(
                "Classification %d for subject %d which is not in the subject table",
                subject_classification["classification_id"],
                subject.subject_id,
            )
            continue

        database_entry = voidorchestra.db.Classification(
            classification_id=subject_classification["classification_id"],
            stamp_id=subject.stamp.stamp_id,
            subject_id=subject.subject_id,
            workflow_id=workflow_id,
            reducer_key=subject_classification["reducer_key"],
            classification=subject_classification["answer_index"],
        )

        # check if we have a classification already -- do this via subject
        # rather than classification id
        classification_exists = bool(
            session.query(voidorchestra.db.Classification)
            .filter(voidorchestra.db.Classification.subject_id == database_entry.subject_id)
            .first()
        )

        # since classifications can change with enough consensus from new
        # classifications, we allow a merge here
        if classification_exists:
            session.merge(database_entry)
        else:
            session.add(database_entry)

        # The subject may be retired if it has been classified enough times, but
        # also possible that the subject was un-retired if it has been moved
        # around
        try:
            subject_zoo = Subject.find(subject.subject_id)
            retired_status = bool(subject_zoo.subject_workflow_status(workflow_id).raw["retired_at"])
            if retired_status != subject.retired:
                subject.retired = retired_status
        except StopIteration:  # stop iteration raised when subject is not in the workflow
            pass

        num_subjects_linked += 1

        # commit changes
        if (i + 1) % commit_frequency == 0:
            voidorchestra.db.commit_database(session)
            logger.debug(
                "Processed %d/%d (%.0f%%) classifications",
                i + 1,
                num_classifications,
                (i + 1) / num_classifications * 100,
            )

    voidorchestra.db.commit_database(session)

    logger.debug(
        "Processed %d/%d (100%%) classifications",
        num_classifications,
        num_classifications,
    )

    return num_subjects_linked


def update_classification_database(workflow_id: str | int = None, commit_frequency: int = 250) -> None:
    """Update the classification database.

    Updates the classification database with new classifications and merges
    changes in consensus into already classified subjects. Each subject is
    individually checked for a classification, therefore no classification data
    is required to be downloaded from Caesar.

    Parameters
    ----------
    workflow_id : str | int
        The ID for the workflow to get classifications from, by default None.
        With the value of None, the value of workflow_id in molemarshal.ini
        will be used.
    commit_frequency : int, optional
        The frequency of which to make commits to the database, by default 250.
        This should be greater than 0.

    Raises
    ------
    ValueError
        Raised by the commit frequency is not a sensible number.
    Exception
        Raised, with a traceback, when the workflow of the given ID cannot
        be found.
    """
    if not workflow_id:
        workflow_id = voidorchestra.config["ZOONIVERSE"]["workflow_id"]

    if commit_frequency <= 0:
        raise ValueError("The commit frequency should be positive and non-zero")

    try:
        workflow = Workflow.find(workflow_id)
    except PanoptesAPIException as exc:
        raise ValueError(
            f"Unable to open the workflow with ID {workflow_id}. Check that is exists and you have permission."
        ).with_traceback(exc.__traceback__)

    with Session(
        engine := voidorchestra.db.connect_to_database_engine(voidorchestra.config["PATHS"]["database"]), info={"url": engine.url}
    ) as session:
        workflow_classifications = get_workflow_classifications(session, workflow_id)
        num_classifications = len(workflow_classifications)

        logger.debug("%d classifications to process", num_classifications)

        num_classifications_linked = process_workflow_classifications(
            session, workflow_classifications, workflow.id, commit_frequency
        )

    if num_classifications_linked == 0:
        logger.info("No classifications were linked to any subjects or stamps")
    else:
        logger.info(
            "%d of %d classifications were linked to subjects or stamps (%.0f %%)",
            num_classifications_linked,
            num_classifications,
            num_classifications_linked / num_classifications * 100,
        )
