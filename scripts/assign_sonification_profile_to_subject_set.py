"""

"""
from datetime import datetime
from logging import Logger, INFO
from typing import Any, Dict, List

from panoptes_client import Project as PanoptesProject
from sqlalchemy.orm import Session
from tqdm import tqdm

from voidorchestra import config, config_paths
from voidorchestra.db import commit_database, connect_to_database_engine
from voidorchestra.db.lightcurve.synthetic import LightcurveSyntheticRegular
from voidorchestra.db.lightcurve_collection import LightcurveCollection
from voidorchestra.db.qpo_model import QPOModel, QPOModelBPL, QPOModelComposite, QPOModelLorentzian
from voidorchestra.db.sonification import Sonification, create_sonification
from voidorchestra.db.sonification_profile import SonificationProfile
from voidorchestra.log import get_logger
from voidorchestra.process.lightcurves import create_synthetic_regular_lightcurves
from voidorchestra.zooniverse.zooniverse import connect_to_zooniverse, open_zooniverse_project
from voidorchestra.zooniverse.subjects import upload_sonifications_to_panoptes_subject_set

logger: Logger = get_logger(__name__.replace(".", "-"))


with Session(
    engine := connect_to_database_engine(config_paths["database"]),
    info={"url": engine.url}
) as session:
    sonifications_to_upload: List[Sonification] = []

    for sonification_profile in session.query(SonificationProfile).all():
        print(f"Checking sonifications for profile '{sonification_profile}':")


        for sonification in session.query(Sonification).filter(
                Sonification.sonification_profile == sonification_profile,
        ):
            if not sonification.subject:
                sonifications_to_upload.append(sonification)

    connect_to_zooniverse()
    project: PanoptesProject = open_zooniverse_project(
        config['ZOONIVERSE'].getint('project_id'),
    )
    upload_sonifications_to_panoptes_subject_set(
        panoptes_workflow_id=28705,
        panoptes_subject_set_id=None,
        subject_set_name=f"{sonification_profile}",
        commit_frequency=1000,
    )
    print(f"Uploaded {len(sonifications_to_upload)} to Zooniverse")
