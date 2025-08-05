"""
Create sonification files for yet-to-be-processed sonifications
"""

from typing import List

import click
from sqlalchemy.orm import Session

from voidorchestra import config_paths
from voidorchestra.db import Sonification, commit_database, connect_to_database_engine
from voidorchestra.process.sonification import write_sonification_files


@click.command(name="sonifications", help="Create sonifications for sonification descriptors that have not yet been produced.")
@click.option(
    "-r",
    "--regenerate",
    is_flag=True,
    default=False,
    help="Whether to do a full re-generation, including re-making sonification files.",
)
@click.pass_context
def create_sonifications(ctx: dict, regenerate: bool = False) -> None:
    """
    Create sonifications for sonification descriptors that have not yet been produced.
    """
    with Session(
        engine := connect_to_database_engine(config_paths["database"]),
        info={"url": engine.url},
    ) as session:
        if regenerate:
            sonifications: List[Sonification] = session.query(Sonification).all()
        else:
            sonifications: List[Sonification] = session.query(Sonification).filter_by(processed=False).all()

        if not sonifications:
            click.echo("No un-processed sonifications!")
        else:
            write_sonification_files(session, sonifications)
            click.echo(f"Generated {len(sonifications)} sonifications from sonification descriptors.")
            session.add_all(sonifications)
            commit_database(session)
