import click
from click import Context
from panoptes_client import Subject as PanoptesSubject, SubjectSet as PanoptesSubjectSet
from panoptes_client.panoptes import PanoptesAPIException
from sqlalchemy.orm import Query, Session
from tqdm import tqdm

from voidorchestra import config_paths
from voidorchestra.db import Subject as LocalSubject, SubjectSet as LocalSubjectSet, connect_to_database_engine
from voidorchestra.zooniverse.zooniverse import connect_to_zooniverse


@click.group()
def local():
    """
    Admin for the local DB.

    This set of commands can be used to carry out administrative tasks which
    are generally helpful during development of a new workflow or project.
    """

@local.command(name="clean-subject-sets")
@click.pass_context
def remove_local_subject_sets(ctx: Context):
    """
    Remove old and/or broken subject sets from the local Void Orchestra database.

    This should be used periodically when making changes to the Void Orchestra
    project in the web interface, as otherwise the database will become
    out of sync.
    """
    connect_to_zooniverse()
    with Session(
            engine := connect_to_database_engine(config_paths["database"]),
            info={'url': engine.url},
    ) as session:
        local_subject_sets: Query[LocalSubjectSet] = session.query(LocalSubjectSet)

        if local_subject_sets.count() == 0:
            click.echo("There are no subject sets in the Void Orchestra database")
            return

        for local_subject_set in tqdm(
            local_subject_sets,
            desc="Removing dead subject sets from database",
            unit="subject sets",
            total=local_subject_sets.count(),
            leave=ctx.obj["VERBOSE"] or ctx.obj["DEBUG"],
        ):
            try:
                _ = PanoptesSubjectSet.find(local_subject_set.zooniverse_subject_set_id)
            except PanoptesAPIException:
                session.delete(local_subject_set)

        session.commit()


@local.command(name="cleanup-subjects")
@click.pass_context
def remove_local_subjects(ctx: Context) -> None:
    """
    Remove old and/or broken subjects from the local Void Orchestra database.

    This should be used periodically when making changes to the Void Orchestra
    project in the web interface, as otherwise the database will become
    out of sync.
    """
    connect_to_zooniverse()
    with Session(
            engine := connect_to_database_engine(config_paths["database"]),
            info={'url': engine.url},
    ) as session:
        local_subjects: Query[LocalSubject] = session.query(LocalSubject)

        if local_subjects.count() == 0:
            click.echo("There are no subjects in the Void Orchestra database")
            return

        for local_subject in tqdm(
            local_subjects,
            desc="Removing dead subjects from database",
            unit="subjects",
            total=local_subjects.count(),
            leave=ctx.obj["VERBOSE"] or ctx.obj["DEBUG"],
        ):
            try:
                _ = PanoptesSubject.find(local_subject.zooniverse_subject_id)
            except PanoptesAPIException:
                session.delete(local_subject)

        session.commit()
