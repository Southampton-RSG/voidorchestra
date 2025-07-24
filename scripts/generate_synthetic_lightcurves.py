"""

"""
from datetime import datetime
from logging import INFO, Logger
from typing import Any, Dict, List

from sqlalchemy.orm import Session
from tqdm import tqdm

from voidorchestra import config_paths
from voidorchestra.db import commit_database, connect_to_database_engine
from voidorchestra.db.lightcurve.synthetic import LightcurveSyntheticRegular
from voidorchestra.db.lightcurve_collection import LightcurveCollection
from voidorchestra.db.qpo_model import QPOModel, QPOModelBPL, QPOModelComposite, QPOModelLorentzian
from voidorchestra.db.sonification import Sonification, create_sonification
from voidorchestra.db.sonification_profile import SonificationProfile
from voidorchestra.log import get_logger
from voidorchestra.process.lightcurves import create_synthetic_regular_lightcurves

logger: Logger = get_logger(__name__.replace(".", "-"))


with Session(
    engine := connect_to_database_engine(config_paths["database"]),
    info={"url": engine.url}
) as session:

    lightcurve_collection: LightcurveCollection = LightcurveCollection(
        name="Initial Synthetic Batch"
    )
    session.add(lightcurve_collection)

    qpo_models: List[QPOModel] = []

    for fraction_bpl, fraction_lorentzian in [
        [.4, .0], [.3, .1], [.2, .2], [.1, .3], [.0, .4]
    ]:
        model_name: str = f"Initial Synthetic Batch: L {fraction_lorentzian}/B {fraction_bpl}"

        if not fraction_lorentzian == 0:
            qpo_model: QPOModel = QPOModelBPL(
                name=model_name,
                coherence=5.0,
                period_value=21,
                period_format="jd",
                variance_fraction=fraction_bpl,
            )
            session.add(qpo_model)

        elif fraction_bpl == 0:
            qpo_model: QPOModel = QPOModelLorentzian(
                name=model_name,
                coherence=5.0,
                period_value=21,
                period_format="jd",
                variance_fraction=fraction_bpl,
            )
            session.add(qpo_model)

        else:
            qpo_model: QPOModel = QPOModelComposite()
            session.add(qpo_model)
            qpo_model_bpl: QPOModel = QPOModelBPL(
                name=model_name,
                qpo_model_parent=qpo_model,
                coherence=5.0,
                period_value=21,
                period_format="jd",
                variance_fraction=fraction_bpl,
            )
            session.add(qpo_model_bpl)
            qpo_model_lorentzian: QPOModel = QPOModelLorentzian(
                name=model_name,
                qpo_model_parent=qpo_model,
                coherence=5.0,
                period_value=21,
                period_format="jd",
                variance_fraction=fraction_lorentzian,
            )
            session.add(qpo_model_lorentzian)

        qpo_models.append(qpo_model)

    parameter_grid: Dict[str, Any] = {
        'start_time': datetime.now(),
        'rate_mean_value': 25,
        'rate_mean_units': '1 / s',
        'cadence_value': 3,
        'cadence_format': 'jd',
        'observation_count': 100,
        'qpo_model': qpo_models,
    }
    synthetic_lightcurves: List[LightcurveSyntheticRegular] = create_synthetic_regular_lightcurves(
        lightcurve_collection, parameter_grid, session,
    )
    sonification_repeats: int = 5
    sonifications: List[Sonification] = []

    for sonification_profile in [
        session.query(SonificationProfile).filter(SonificationProfile.name == "Guitar, Medium").one(),
        session.query(SonificationProfile).filter(SonificationProfile.name == "Flute, Long, Medium").one(),
        session.query(SonificationProfile).filter(SonificationProfile.name == "Piano, Medium").one(),
    ]:
        for n, synthetic_lightcurve in enumerate(
            progress_bar := tqdm(
                synthetic_lightcurves * sonification_repeats,
                "defining sonifications for synthetic lightcurves",
                unit="sonifications",
                leave=logger.level <= INFO,
                disable=logger.level > INFO,
            )
        ):
            sonifications.append(
                create_sonification(
                    lightcurve=synthetic_lightcurve,
                    sonification_profile=sonification_profile,
                )
            )

    print(f"Created {len(sonifications)} sonifications.")

    session.add_all(sonifications)
    commit_database(session)
