from itertools import product
from logging import Logger
from typing import Any, Dict, Generator, List

from sqlalchemy.orm import Session

from voidorchestra.db import LightcurveCollection, LightcurveSyntheticRegular
from voidorchestra.log import get_logger

logger: Logger = get_logger(__name__.replace(".", "-"))


def generate_parameter_grid(
    parameter_grid: Dict[str, Any],
) -> Generator[Dict, Dict, None]:
    """
    Turns a dictionary into a generator that yields a parameter grid.

    :url: https://stackoverflow.com/questions/65392737/python-how-to-create-a-parameter-grid-with-dynamic-number-of-parameters

    Parameters
    ----------
    parameter_grid: Dict[str, Any]

    Yields
    ------
    parameter_combination: Dict[str, Any]
        A point on the parameter grid.
    """
    fixed_parameters: Dict[str, Any] = {key: value for key, value in parameter_grid.items() if not isinstance(value, list)}
    varying_parameters: Dict[str, Any] = {key: value for key, value in parameter_grid.items() if isinstance(value, list)}

    for value_combinations in product(*varying_parameters.values()):
        parameter_combination: Dict[str, Any] = fixed_parameters | dict(zip(varying_parameters.keys(), value_combinations))
        yield parameter_combination


def create_synthetic_regular_lightcurves(
    lightcurve_collection: LightcurveCollection,
    parameter_grid: Dict[str, Any],
    session: Session,
):
    """
    Creates synthetic lightcurves covering the specified parameter grid.

    Parameters
    ----------
    lightcurve_collection: LightcurveCollection
        The collection to create the lightcurves within.
    parameter_grid: Dict[str, Any]
        The grid of parameters to generate sets over.
    session: Session
        The database session.

    Returns
    -------
    synthetic_lightcurves: LightcurveSynthetic
        The created lightcurves.
    """
    synthetic_lightcurves: List[LightcurveSyntheticRegular] = []

    for parameters in generate_parameter_grid(parameter_grid):
        lightcurve: LightcurveSyntheticRegular = LightcurveSyntheticRegular(
            observation_start=parameters["observation_start"],
            observation_count=parameters["observation_count"],
            cadence_value=parameters["cadence_value"],
            cadence_format=parameters["cadence_format"],
            rate_mean_value=parameters["rate_mean_value"],
            rate_mean_units=parameters["rate_mean_units"],
            exposure_value=parameters["exposure_value"],
            exposure_units=parameters["exposure_units"],
            qpo_model=parameters["qpo_model"],
            lightcurve_collection=lightcurve_collection,
        )
        synthetic_lightcurves.append(lightcurve)
        session.add(lightcurve)

    return synthetic_lightcurves
