"""
Generates synthetic lightcurves

Call using python scripts/generate_synthetic_lightcurves.py
"""
from datetime import datetime
from logging import INFO, Logger
from typing import Any, Dict, List

from astropy import units as u
from astropy.units import Quantity
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
from voidorchestra.process.lightcurves import create_synthetic_regular_lightcurves, generate_parameter_grid

logger: Logger = get_logger(__name__.replace(".", "-"))


MODEL_PARAMETER_GRID: dict[str, Any] = {
    'drw_long_period': [Quantity(10**6, 's'), Quantity(10**6.5, 's')],
    'drw_long_power_fraction': 0.2,
    'drw_short_period': [Quantity(10**4.5, 's'), Quantity(10**5.5, 's')],
    'drw_short_power_fraction': 0.2,
    'lorentzian_period': Quantity(1.0e6, 's'),
    'lorentzian_power_fraction': [0, 0.5],
    'lorentzian_coherence': [5, 10],
}
SIMULATION_PARAMETER_GRID: Dict[str, Any] = {
    "observation_start": datetime.now(),
    "rate_mean_value": 25,
    "rate_mean_units": "1 / s",
    "cadence_value": 3,
    "cadence_format": "jd",
    "exposure_value": 1,
    "exposure_units": "s",
    "observation_count": 100,
}


with Session(
    engine := connect_to_database_engine(config_paths["database"]),
    info={"url": engine.url}
) as session:
    # Has this already been done?
    if found_lightcurve_collection := session.query(LightcurveCollection).where(
            LightcurveCollection.name == "Initial Synthetic Batch"
    ).all():
        print(f"Found already-generated lightcurves: {found_lightcurve_collection}")
        exit()

    # Set up the lightcurve collection to collect all these
    lightcurve_collection: LightcurveCollection = LightcurveCollection(
        name="Initial Synthetic Batch"
    )
    session.add(lightcurve_collection)

    qpo_models: List[QPOModel] = []

    for parameters in generate_parameter_grid(MODEL_PARAMETER_GRID):
        qpo_model_parent: QPOModel = QPOModelComposite()
        session.add(qpo_model_parent)
        commit_database(session)

        qpo_model_drw_short: QPOModelBPL = QPOModelBPL(
            name=f"Long DRW (period: {parameters['drw_long_period']}, frac: {parameters['drw_long_power_fraction']})",
            qpo_model_parent_id=qpo_model_parent.id,
            coherence=1.0,
            period_value=parameters["drw_long_period"].to(u.d).value,
            period_format="jd",
            variance_fraction=parameters["drw_long_power_fraction"],
        )
        session.add(qpo_model_drw_short)

        qpo_model_drw_short: QPOModelBPL = QPOModelBPL(
            name=f"Long DRW (period: {parameters['drw_long_period']}, frac: {parameters['drw_long_power_fraction']})",
            qpo_model_parent_id=qpo_model_parent.id,
            coherence=1.0,
            period_value=parameters["drw_short_period"].to(u.d).value,
            period_format="jd",
            variance_fraction=parameters["drw_short_power_fraction"],
        )
        session.add(qpo_model_drw_short)

        qpo_model_lorentzian: QPOModelLorentzian = QPOModelLorentzian(
            name=f"Lorentzian (period: {parameters['lorentzian_period']}, frac: {parameters['lorentzian_power_fraction']}",
            qpo_model_parent_id=qpo_model_parent.id,
            coherence=10.0,
            period_value=parameters["lorentzian_period"].to(u.d).value,
            period_format="jd",
            variance_fraction=parameters["lorentzian_power_fraction"],
        )
        session.add(qpo_model_lorentzian)

        commit_database(session)

        qpo_models.append(qpo_model_parent)


    simulation_parameter_grid: Dict[str, Any] = SIMULATION_PARAMETER_GRID.copy()
    simulation_parameter_grid["qpo_model"] = qpo_models

    synthetic_lightcurves: List[LightcurveSyntheticRegular] = create_synthetic_regular_lightcurves(
        lightcurve_collection, simulation_parameter_grid, session,
    )
    sonification_repeats: int = 3
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

    print(f"Created {len(synthetic_lightcurves)} lightcurves, {len(sonifications)} sonifications.")

    session.add_all(sonifications)
    commit_database(session)
