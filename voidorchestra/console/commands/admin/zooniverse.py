from typing import List

import click
from click import Context
from panoptes_client import Subject as PanoptesSubject, SubjectSet as PanoptesSubjectSet

from voidorchestra import config
from voidorchestra.zooniverse.zooniverse import connect_to_zooniverse


@click.group()
def zooniverse():
    """
    Admin for the Zooniverse DB via Panoptes.

    This set of commands can be used to carry out administrative tasks which
    are generally helpful during development of a new workflow or project.
    """


@zooniverse.command(name="clean-subjects")
@click.pass_context
def clean_loose_zooniverse_subjects(
    ctx: Context,  # noqa: D417
) -> None:
    """
    Remove subjects without a subject set from the Zooniverse database.

    It's possible to get out of sync and accidentally have loose subjects,
    usually during development. This tidies them away.
    """
    connect_to_zooniverse()

    panoptes_subjects: List[PanoptesSubject] = list(
        PanoptesSubject.where(
            project_id=config["ZOONIVERSE"].getint("project_id"),
        )
    )
    panoptes_subject_set: PanoptesSubjectSet = PanoptesSubjectSet.find(
        config["ZOONIVERSE"].getint("subject_set_id"),
    )

    print(f"Found up to {len(panoptes_subjects)} subjects for project")

    num_deleted_panoptes_subjects: int = 0

    for panoptes_subject in panoptes_subjects:
        if not len(list(panoptes_subject.links.subject_sets)):
            panoptes_subject_set.add(panoptes_subject)
            num_deleted_panoptes_subjects += 1

    # Doesn't work if you don't move them to the subject set first?
    for panoptes_subject in panoptes_subject_set.subjects:
        panoptes_subject.delete()

    click.echo(f"Deleted {num_deleted_panoptes_subjects} subject(s) with no subject set.")
