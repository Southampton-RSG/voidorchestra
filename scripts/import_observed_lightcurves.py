"""
Imports observed lightcurves into the database
"""
from datetime import datetime
from logging import INFO, Logger, DEBUG
from pathlib import Path
from typing import Any, Dict, List

from astropy import units as u
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session
from tqdm import tqdm

from voidorchestra import config_paths
from voidorchestra.db import Lightcurve, LightcurveCollection, LightcurveFile, commit_database, connect_to_database_engine
from voidorchestra.db.sonification import Sonification, create_sonification
from voidorchestra.db.sonification_profile import SonificationProfile
from voidorchestra.log import get_logger, set_logger_levels


logger: Logger = get_logger(__name__.replace(".", "-"))


with Session(
    engine := connect_to_database_engine(config_paths["database"]),
    info={"url": engine.url}
) as session:
    lightcurve_path: Path = config_paths["lightcurves"]
    set_logger_levels(DEBUG)

    if found_lightcurves := session.query(LightcurveFile).where(LightcurveFile.name == "RE_J1034+396").all():
        print(f"Found already-imported lightcurves: {found_lightcurves}")
        exit()

    lightcurve_collection_j1034: LightcurveCollection = LightcurveCollection(
        name="Initial RE_J1034+396 Batch"
    )
    session.add(lightcurve_collection_j1034)

    lightcurve_j1034: LightcurveFile = LightcurveFile(
        name="RE_J1034+396",
        path=str(lightcurve_path / "RE_J1034+396" / "RE_J1034+396.dat"),
        file_format="ascii",
        time_column="time",
        time_format="cxcsec",
        rate_column="rate",
        rate_units="1 / s",
        exposure_column="exposure",
        exposure_units="s",
        error_column="err",
        error_units="1 / s",
        lightcurve_collection=lightcurve_collection_j1034,
    )
    session.add(lightcurve_j1034)

    lightcurve_j1034_subsets: List[LightcurveFile] = lightcurve_j1034.get_subsets(
        subsets=5, observation_length=17.3 * 3550 * u.s,
    )
    print(f"Created subsets of {lightcurve_j1034}: {lightcurve_j1034_subsets}")
    session.add_all(lightcurve_j1034_subsets)
    commit_database(session)

    lightcurve_collection_j1430: LightcurveCollection = LightcurveCollection(
        name="Initial SDSS_J1430+2303 Batch"
    )
    session.add(lightcurve_collection_j1430)
    lightcurve_j1430: LightcurveFile = LightcurveFile(
        name="SDSS_J1430+2303",
        path=str(lightcurve_path / "SDSS_J1430+2303" / "table_httpsirsa.ipac.caltech.educgi-bing2pnp.csv"),
        file_format="ascii.csv",
        time_column="mjd",
        time_format="mjd",
        rate_column="mag",
        rate_units="",
        error_column="magerr",
        error_units="",
        exposure_column="exptime",
        exposure_units="s",
        lightcurve_collection=lightcurve_collection_j1430,
    )
    session.add(lightcurve_j1430)

    lightcurve_j1430_subsets: List[LightcurveFile] = lightcurve_j1430.get_subsets(
        subsets=5, observation_length=100 * u.d,
    )
    print(f"Created subsets of {lightcurve_j1430}: {lightcurve_j1430_subsets}")
    session.add_all(lightcurve_j1430_subsets)
    commit_database(session)

    sonifications: List[Sonification] = []

    for sonification_profile in [
        session.query(SonificationProfile).filter(SonificationProfile.name == "Guitar, Medium").one(),
        session.query(SonificationProfile).filter(SonificationProfile.name == "Flute, Long, Medium").one(),
        session.query(SonificationProfile).filter(SonificationProfile.name == "Piano, Medium").one(),
    ]:
        for n, lightcurve_subset in enumerate(
            progress_bar := tqdm(
                lightcurve_j1034_subsets+lightcurve_j1430_subsets,
                "defining sonifications for lightcurve subsets",
                unit="sonifications",
                leave=logger.level <= INFO,
                disable=logger.level > INFO,
            )
        ):
            sonifications.append(
                create_sonification(
                    lightcurve=lightcurve_subset,
                    sonification_profile=sonification_profile,
                )
            )

    print(f"Created sonifications: {sonifications}")
    session.add_all(sonifications)

    commit_database(session)
