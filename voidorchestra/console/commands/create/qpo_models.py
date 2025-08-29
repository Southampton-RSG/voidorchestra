"""
Create PSD images for QPO models
"""

from typing import List

import click
from sqlalchemy.orm import Session

from voidorchestra import config_paths
from voidorchestra.db import QPOModel, commit_database, connect_to_database_engine
from voidorchestra.process.qpo_models import write_psd_images


@click.command(name="psd", help="Create PSD plots for QPO models.")
@click.pass_context
def create_psds(ctx: dict) -> None:
    """
    Create sonifications for sonification descriptors that have not yet been produced.
    """
    with Session(
        engine := connect_to_database_engine(config_paths["database"]),
        info={"url": engine.url},
    ) as session:
        qpo_models: List[QPOModel] = session.query(QPOModel).where(QPOModel.qpo_model_parent_id == None).all()

        if not qpo_models:
            click.echo("No QPO models in DB!")
        else:
            click.echo(f"Processing {len(qpo_models)} QPO models.")
            write_psd_images(qpo_models)
            click.echo(f"Generated {len(qpo_models)} PSDs from QPO models.")
            commit_database(session)
