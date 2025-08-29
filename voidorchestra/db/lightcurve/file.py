#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
For lightcurves loaded from files on disk
"""

from logging import Logger
from pathlib import Path
from random import randint
from typing import Dict, List

import numpy as np
from astropy.time import Time, TimeDelta
from astropy.timeseries import TimeSeries
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from voidorchestra.db.lightcurve import Lightcurve
from voidorchestra.log import get_logger

logger: Logger = get_logger(__name__.replace(".", "-"))


class LightcurveFile(Lightcurve):
    """
    Observational lightcurve loaded from file.

    Attributes
    ----------
    rate_mean_value: float
        Mean rate of simulated observations, unit is 'per second'.
    rate_mean_units: str
        The units of the mean rate.
    qpo_model_id: int
        The ID of the QPO model this lightcurve uses.
    qpo_model: relationship
        The QPO model used to generate the synthetic lightcurve.
    random_state: int
        The random seed for the simulation.
    """

    path: Mapped[str] = mapped_column(String(256), nullable=True)

    file_format: Mapped[str] = mapped_column(String(32), nullable=True)

    time_column: Mapped[str] = mapped_column(String(32), nullable=True)
    time_format: Mapped[str] = mapped_column(String(32), nullable=True)
    rate_column: Mapped[str] = mapped_column(String(32), nullable=True)
    rate_units: Mapped[str] = mapped_column(String(32), nullable=True)
    error_column: Mapped[str] = mapped_column(String(32), nullable=True)
    error_units: Mapped[str] = mapped_column(String(32), nullable=True)
    exposure_column: Mapped[str] = mapped_column(String(32), nullable=True)
    exposure_units: Mapped[str] = mapped_column(String(32), nullable=True)

    observation_index_start: Mapped[int] = mapped_column(nullable=True)
    observation_index_finish: Mapped[int] = mapped_column(nullable=True)

    __mapper_args__: Dict[str, str] = {
        "polymorphic_identity": "lightcurve_file",
    }

    def __repr__(self):
        return f"LightcurveFile(id={self.id}, name={self.name!r})"

    def get_data(
        self,
        **kwargs,
    ) -> TimeSeries:
        """
        Returns the data associated with the lightcurve.

        Parameters
        ----------
        kwargs: None

        Returns
        -------
        lightcurve: TimeSeries
            The timeseries of data for the lightcurve
        """
        timeseries: TimeSeries = TimeSeries.read(
            Path(self.path),
            format=self.file_format,
            time_column=self.time_column,
            time_format=self.time_format,
            units={
                self.rate_column: self.rate_units,
                self.error_column: self.error_units,
                self.exposure_column: self.exposure_units,
            },
        )
        timeseries.rename_columns(
            [self.rate_column, self.error_column, self.exposure_column],
            ["rate", "error", "exposure"],
        )

        if self.observation_index_start is not None:
            return timeseries.iloc[self.observation_index_start : self.observation_index_finish]

        else:
            return timeseries

    def get_subsets(
        self,
        subsets: int,
        observation_length: TimeDelta,
    ):
        """

        Parameters
        ----------
        subsets: int
            Number of sub-lightcurves to produce
        observation_length: TimeDelta
            Length of each sub-lightcurve

        Returns
        -------
        lightcurve_file_subsets: List[LightcurveFile]
            The subsets, as their own LightcurveFile DB entries.
        """
        timeseries: TimeSeries = self.get_data()
        lightcurve_file_subsets: List[Lightcurve] = []

        observation_finish_valid: Time = timeseries.iloc[-1]["time"] - observation_length
        observation_count: int = len(timeseries[timeseries["time"] < observation_finish_valid])

        for i in range(subsets):
            # This loop is to ensure that we don't settle on a range that has no actual lightcurve data in it
            # We pick a start time by index, then a chunk of data after it, and discard the attempt if that
            # data is too short
            observation_window_found: bool = False
            for i in range(3):
                observation_index_start: int = randint(0, observation_count)
                observation_start: Time = timeseries.iloc[observation_index_start]["time"]
                observation_finish: Time = observation_start + observation_length
                observation_index_finish: int = np.argmax(timeseries["time"] > observation_finish)

                if not observation_index_finish:
                    observation_index_finish = -1

                observations_count_in_window: int = len(timeseries.iloc[observation_index_start:observation_index_finish])
                if observations_count_in_window > 10:
                    observation_window_found = True
                    break

            if observation_window_found:
                lightcurve_file_subset: LightcurveFile = LightcurveFile(
                    name=f"{self.name} {observation_start.to_datetime():%y-%m-%d:%H-%M} - {observation_finish.to_datetime():%y-%m-%d:%H-%M}",
                    path=self.path,
                    file_format=self.file_format,
                    time_column=self.time_column,
                    time_format=self.time_format,
                    rate_column=self.rate_column,
                    rate_units=self.rate_units,
                    error_column=self.error_column,
                    error_units=self.error_units,
                    exposure_column=self.exposure_column,
                    exposure_units=self.exposure_units,
                    observation_index_start=observation_index_start,
                    observation_index_finish=int(observation_index_finish),
                    lightcurve_collection=self.lightcurve_collection,
                )
                try:
                    lightcurve_file_subset.get_data()
                except Exception as e:
                    raise e

                lightcurve_file_subsets.append(lightcurve_file_subset)
            else:
                logger.warning(
                    f"Could not find suitable start time for subset of lightcurve: {self}, "
                    f"time range {timeseries.iloc[0]['time'].to_datetime():%y-%m-%d:%H-%M} - {timeseries.iloc[-1]['time'].to_datetime():%y-%m-%d:%H-%M}. "
                    f"Window may be too short, or observations may be too sparse."
                )

        return lightcurve_file_subsets
