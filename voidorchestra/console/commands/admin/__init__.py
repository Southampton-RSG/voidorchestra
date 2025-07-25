#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains sub-commands for `void-orchestra admin`.

The commands should be used for admin and development purposes.
"""

from typing import Dict

import click
from click import Context
from panoptes_client import Project as PanoptesProject, Subject as PanoptesSubject, SubjectSet as PanoptesSubjectSet
from panoptes_client.panoptes import PanoptesAPIException
from sqlalchemy.orm import Query, Session
from tqdm import tqdm

from voidorchestra import config, config_paths
from voidorchestra.console.commands.admin.local import local
from voidorchestra.console.commands.admin.zooniverse import zooniverse
from voidorchestra.db import Subject as LocalSubject, SubjectSet as LocalSubjectSet, connect_to_database_engine
from voidorchestra.zooniverse.zooniverse import connect_to_zooniverse


@click.group()
def admin():
    """
    Admin and project development commands

    This set of commands can be used to carry out administrative tasks which
    are generally helpful during development of a new workflow or project.
    """


admin.add_command(local)
admin.add_command(zooniverse)


@admin.command("move-to-subject-set")
@click.pass_context
@click.argument("old_panoptes_subject_set_id")
@click.argument("new_panoptes_subject_set_id")
def transfer_between_subject_sets(
    ctx: Context, old_panoptes_subject_set_id: str | int, new_panoptes_subject_set_id: str | int
) -> None:
    """
    Move subjects from one subject set to another.

    This is used to move all the subjects in one subject set to another subject
    set, ideally in the same project and workflow.
    """
    connect_to_zooniverse()

    try:
        old_subject_set: PanoptesSubjectSet = PanoptesSubjectSet.find(old_panoptes_subject_set_id)
    except PanoptesAPIException:
        click.echo(f"Cannot access subject set with id {old_panoptes_subject_set_id}")
        return
    try:
        new_subject_set: PanoptesSubjectSet = PanoptesSubjectSet.find(new_panoptes_subject_set_id)
    except PanoptesAPIException:
        click.echo(f"Cannot access subject set with id {new_panoptes_subject_set_id}")
        return

    num_workflows: int = 0
    for _ in new_subject_set.links.workflows:
        num_workflows += 1

    if num_workflows != 1:
        click.echo(
            "This command only supports subject sets with 1 linked workflow, and does not support the subject"
            + f" set {new_panoptes_subject_set_id} with {num_workflows} linked workflows"
        )
        return

    with Session(
        engine := connect_to_database_engine(config_paths["database"]),
        info={"url": engine.url},
    ) as session:
        local_subjects: Query[LocalSubject] = session.query(LocalSubject).filter(
            LocalSubject.zooniverse_subject_set_id == int(old_panoptes_subject_set_id)
        )

        for local_subject in tqdm(
            local_subjects,
            total=local_subjects.count(),
            desc=f"Moving subjects from {old_panoptes_subject_set_id} to {new_panoptes_subject_set_id}",
            unit="subject",
            leave=ctx.obj["VERBOSE"] or ctx.obj["DEBUG"],
        ):
            panoptes_subject: PanoptesSubject = PanoptesSubject.find(local_subject.zooniverse_subject_id)
            old_subject_set.remove(panoptes_subject)
            new_subject_set.add(panoptes_subject)

            local_subject.subject_set_id = int(new_subject_set.id)
            local_subject.workflow_id = new_subject_set.links.workflows[0].id

        old_subject_set.save()
        new_subject_set.save()
        session.commit()


@admin.command(name="move-all-subjects")
@click.pass_context
@click.argument(
    "new_panoptes_subject_set_id",
)
def transfer_all_subjects_to_one_subject_set(
    ctx: Context,  # noqa: D417
    new_panoptes_subject_set_id: int,
) -> None:
    """
    Move all the subjects in a project to one subject set.

    This is used to move all the subjects in a project to one subject set,
    ideally in the same project and workflow.
    """
    connect_to_zooniverse()
    panoptes_project: PanoptesProject = PanoptesProject(config["ZOONIVERSE"]["project_id"])

    try:
        new_panoptes_subject_set: PanoptesSubjectSet = PanoptesSubjectSet.find(new_panoptes_subject_set_id)
    except PanoptesAPIException:
        click.echo(f"Cannot access subject set with id {new_panoptes_subject_set_id}")
        return

    num_panoptes_workflows: int = 0
    for _ in new_panoptes_subject_set.links.workflows:
        num_panoptes_workflows += 1

    if num_panoptes_workflows != 1:
        click.echo(
            "This command only supports subject sets with 1 linked workflow, and does not support the subject"
            + f" set {new_panoptes_subject_set_id} with {num_panoptes_workflows} linked workflows"
        )
        return

    local_subject_set_cache: Dict[int, LocalSubjectSet] = {}

    with Session(
        engine := connect_to_database_engine(config_paths["database"]),
        info={"url": engine.url},
    ) as session:
        local_subjects: Query[LocalSubject] = session.query(LocalSubject).filter(
            LocalSubject.zooniverse_project_id == int(panoptes_project.id)
        )

        for local_subject in tqdm(
            local_subjects,
            total=local_subjects.count(),
            desc=f"Moving subjects to {new_panoptes_subject_set_id}",
            unit="subject",
            leave=ctx.obj["VERBOSE"] or ctx.obj["DEBUG"],
        ):
            panoptes_subject: PanoptesSubject = PanoptesSubject.find(local_subject.zooniverse_subject_id)

            if local_subject.subject_set_id not in local_subject_set_cache:
                old_panoptes_subject_set: PanoptesSubjectSet = PanoptesSubjectSet.find(local_subject.subject_set_id)
                local_subject_set_cache[local_subject.zooniverse_subject_set_id] = old_panoptes_subject_set
            else:
                old_panoptes_subject_set: PanoptesSubjectSet = local_subject_set_cache[
                    local_subject.zooniverse_subject_set_id
                ]

            new_panoptes_subject_set.add(panoptes_subject)
            old_panoptes_subject_set.remove(panoptes_subject)

            local_subject.subject_set_id = int(new_panoptes_subject_set_id)
            local_subject.workflow_id = int(new_panoptes_subject_set.links.workflows[0].id)

        new_panoptes_subject_set.save()
        for local_subject_set in local_subject_set_cache.values():
            local_subject_set.save()

        session.commit()
