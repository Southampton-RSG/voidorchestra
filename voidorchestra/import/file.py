"""
Code for importing observational lightcurves from file
"""

from logging import getLogger
from pathlib import Path
from random import randint
from typing import Dict

from astropy import units as u
from astropy.time import Time
from astropy.timeseries import TimeSeries
from astropy.units import UnitBase

logger = getLogger(__name__)


def load_observational_data_from_file(
    file_path: Path,
    format: str | None = "ascii",
    time_column: str | None = "time",
    time_format: str | None = "mjd",
    units: Dict[str, UnitBase] | None = None,
    column_mapping: Dict[str, str] | None = None,
    length: UnitBase | None = None,
) -> TimeSeries:
    """
    Imports observational data from file

    Parameters
    ----------
    file_path : Path
        Path to the file to import.
    format : str
        File format.
    time_column : str
        Time column name.
    time_format : str
        Format of the time column, in Astropy time format terms.
    units : Dict[str, UnitBase]|None
        A dictionary containing 'name' and 'error' and the units of those columns in the file.
    column_mapping : Dict[str, str]|None
        A dictionary containing 'name' and 'error' and the names of the columns in the file that map onto them.
    length: UnitBase|None
        Length of observation. If provided, selects a subset of the data of this length.

    Returns
    -------
    TimeSeries:
        TimeSeries object containing the observational data.
    """
    if column_mapping is None:
        column_mapping: Dict[str, str] = {
            "rate": "rate",
            "error": "error",
        }
    if units is None:
        units: Dict[str, UnitBase] = {
            "rate": 1 / u.s,
            "error": 1 / u.s,
        }

    lightcurve: TimeSeries = TimeSeries.read(
        file_path,
        format=format,
        time_column=time_column,
        time_format=time_format,
        units=units,
    )

    for file_column, standard_column in column_mapping.items():
        lightcurve.rename_column(file_column, standard_column)

    if length is not None:
        index_start: int = randint(0, len(lightcurve))
        time_start: Time = lightcurve.time[index_start]
        return lightcurve.loc[time_start : time_start + length]

    else:
        return lightcurve
