#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""This module contains sub-commands for `molemarshal admin`.

The commands should be used for admin and development purposes.
"""

from __future__ import annotations

import click
from panoptes_client import Project
from panoptes_client import Subject
from panoptes_client import SubjectSet
from panoptes_client.panoptes import PanoptesAPIException
from sqlalchemy.orm import Session
from tqdm import tqdm

import voidorchestra
import voidorchestra.zooniverse.zooniverse


@click.group()
def admin():
    """Admin and project development commands

    This set of commands can be used to carry out administrative tasks which
    are generally helpful during development of a new workflow or project.
    """


@admin.command(name="cleanup-subjects")
@click.pass_context
def remove_subjects(ctx: click.Context) -> None:
    """Remove old and/ord broken subjects from the MoleMarshal database.

    This should be used periodically when making changes to the MoleMarshal
    project in the web interface, as otherwise the database will become
    out of sync.
    """
    voidorchestra.zooniverse.zooniverse.connect_to_zooniverse()
    with Session(voidorchestra.db.connect_to_database_engine(voidorchestra.config["PATHS"]["database"])) as session:
        subjects = session.query(voidorchestra.db.Subject)

        if subjects.count() == 0:
            click.echo("There are no subjects in the MoleMarshal database")
            return

        for subject in tqdm(
            subjects,
            desc="Removing dead subjects from database",
            unit="subjects",
            total=subjects.count(),
            leave=ctx.obj["VERBOSE"] or ctx.obj["DEBUG"],
        ):
            try:
                _ = Subject.find(subject.subject_id)
            except PanoptesAPIException:
                session.delete(subject)

        session.commit()


@admin.command(name="cleanup-subject-sets")
@click.pass_context
def remove_subject_sets(ctx: click.Context):
    """Remove old and/or broken subject sets from the MoleMarshal database.

    This should be used periodically when making changes to the MoleMarshal
    project in the web interface, as otherwise the database will become
    out of sync.
    """
    voidorchestra.zooniverse.zooniverse.connect_to_zooniverse()
    with Session(voidorchestra.db.connect_to_database_engine(voidorchestra.config["PATHS"]["database"])) as session:
        subject_sets = session.query(voidorchestra.db.SubjectSet)

        if subject_sets.count() == 0:
            click.echo("There are no subject sets in the MoleMarshal database")
            return

        for subject_set in tqdm(
            subject_sets,
            desc="Removing dead subject sets from database",
            unit="subject sets",
            total=subject_sets.count(),
            leave=ctx.obj["VERBOSE"] or ctx.obj["DEBUG"],
        ):
            try:
                _ = SubjectSet.find(subject_set.subject_set_id)
            except PanoptesAPIException:
                session.delete(subject_set)

        session.commit()


@admin.command("move-to-subject-set")
@click.pass_context
@click.argument("old_id")
@click.argument("new_id")
def transfer_between_subject_sets(ctx: click.Context, old_id: str | int, new_id: str | int) -> None:
    """Move subjects from one subject set to another.

    This is used to move all the subjects in one subject set to another subject
    set, ideally in the same project and workflow.
    """
    voidorchestra.zooniverse.zooniverse.connect_to_zooniverse()

    try:
        old_subject_set = SubjectSet.find(old_id)
    except PanoptesAPIException:
        click.echo(f"Cannot access subject set with id {old_id}")
        return
    try:
        new_subject_set = SubjectSet.find(new_id)
    except PanoptesAPIException:
        click.echo(f"Cannot access subject set with id {new_id}")
        return

    num_workflows = 0
    for _ in new_subject_set.links.workflows:
        num_workflows += 1

    if num_workflows != 1:
        click.echo(
            "This command only supports subject sets with 1 linked workflow, and does not support the subject"
            + f" set {new_id} with {num_workflows} linked workflows"
        )
        return

    with Session(voidorchestra.db.connect_to_database_engine(voidorchestra.config["PATHS"]["database"])) as session:
        subjects = session.query(voidorchestra.db.subject.Subject).filter(voidorchestra.db.subject.Subject.subject_set_id == int(old_id))

        for subject in tqdm(
            subjects,
            total=subjects.count(),
            desc=f"Moving subjects from {old_id} to {new_id}",
            unit="subject",
            leave=ctx.obj["VERBOSE"] or ctx.obj["DEBUG"],
        ):
            subject_zoo = Subject.find(subject.subject_id)
            old_subject_set.remove(subject_zoo)
            new_subject_set.add(subject_zoo)

            subject.subject_set_id = int(new_subject_set.id)
            subject.workflow_id = new_subject_set.links.workflows[0].id

        old_subject_set.save()
        new_subject_set.save()
        session.commit()


@admin.command(name="move-all-subjects")
@click.pass_context
@click.argument("new_id")
def transfer_all_stamps_to_one_subject_set(ctx: click.Context, new_id: int) -> None:
    """Move all the subjects in a project to one subject set.

    This is used to move all the subjects in a project to one subject set,
    ideally in the same project and workflow.
    """
    voidorchestra.zooniverse.zooniverse.connect_to_zooniverse()
    project = Project(voidorchestra.config["ZOONIVERSE"]["project_id"])

    try:
        new_subject_set = SubjectSet.find(new_id)
    except PanoptesAPIException:
        click.echo(f"Cannot access subject set with id {new_id}")
        return

    num_workflows = 0
    for _ in new_subject_set.links.workflows:
        num_workflows += 1

    if num_workflows != 1:
        click.echo(
            "This command only supports subject sets with 1 linked workflow, and does not support the subject"
            + f" set {new_id} with {num_workflows} linked workflows"
        )
        return

    subject_set_cache = {}

    with Session(voidorchestra.db.connect_to_database_engine(voidorchestra.config["PATHS"]["database"])) as session:
        subjects = session.query(voidorchestra.db.subject.Subject).filter(voidorchestra.db.subject.Subject.project_id == int(project.id))

        for subject in tqdm(
            subjects,
            total=subjects.count(),
            desc=f"Moving subjects to {new_id}",
            unit="subject",
            leave=ctx.obj["VERBOSE"] or ctx.obj["DEBUG"],
        ):
            subject_zoo = Subject.find(subject.subject_id)

            if subject.subject_set_id not in subject_set_cache:
                old_subject_set = SubjectSet.find(subject.subject_set_id)
                subject_set_cache[subject.subject_set_id] = old_subject_set
            else:
                old_subject_set = subject_set_cache[subject.subject_set_id]

            new_subject_set.add(subject_zoo)
            old_subject_set.remove(subject_zoo)

            subject.subject_set_id = int(new_id)
            subject.workflow_id = int(new_subject_set.links.workflows[0].id)

        new_subject_set.save()
        for subject_set in subject_set_cache.values():
            subject_set.save()

        session.commit()
