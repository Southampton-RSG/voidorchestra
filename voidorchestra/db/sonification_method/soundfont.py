#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Defines the database object for sonification methods using soundfonts.
"""
from json import loads
from logging import Logger
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Tuple

from astropy.timeseries import TimeSeries
from numpy import floating
from numpy.typing import NDArray
from pandas import DataFrame, read_csv
from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship
from strauss.generator import Sampler
from strauss.score import Score
from strauss.sonification import Sonification as StraussSonification
from strauss.sources import Events

from voidorchestra import config_paths
from voidorchestra.db.sonification_method import SonificationMethod
from voidorchestra.log import get_logger

if TYPE_CHECKING:
    from voidorchestra.db import SonificationProfile

logger: Logger = get_logger(__name__.replace(".", "-"))


class SonificationMethodSoundfont(SonificationMethod):
    """
    Shared-table inheritance subclass for Soundfont sonification methods.

    Attributes
    ----------
    preset:
        aaa
    preset_modification:
        aaa
    path:
        aaae
    continuous:
        aaa
    """
    preset: Mapped[int] = mapped_column(Integer(), nullable=True)
    preset_modification: Mapped[str] = mapped_column(Text(), nullable=True)
    path: Mapped[str] = mapped_column(String(256), nullable=False)
    continuous: Mapped[bool] = mapped_column(Boolean(), nullable=False)

    sonification_profiles: Mapped[List['SonificationProfile']] = relationship(back_populates='sonification_method')

    SYSTEM: str = 'mono'

    COLUMNS: List[str] = [
        'preset_modification', 'path', 'continuous', 'preset'
    ]

    __mapper_args__: Dict[str, str] = {
        'polymorphic_identity': 'sonification_method_soundfont',
    }

    def __repr__(self) -> str:
        return f"SonificationMethodSoundfont(id={self.id!r})"

    def sonify_lightcurve(
            self,
            score: Score,
            lightcurve: TimeSeries,
    ) -> StraussSonification:
        """
        Gets the generator used to sonify the data by this method.

        Parameters
        ----------
        score: Score
            The key and tempo used (set by the sonification profile).
        lightcurve: TimeSeries
            The data to sonify.

        Returns
        -------
        StraussSonification:
            The sonified sound.
        """
        sampler: Sampler = Sampler(
            config_paths['soundfonts'] / self.path,
            sf_preset=self.preset
        )
        if self.preset_modification:
            try:
                sampler.modify_preset(
                    loads(self.preset_modification)
                )
            except Exception as e:
                logger.error(
                    f"Error in JSON: {self.preset_modification}: {e}"
                )

        maps: Dict[str, NDArray[floating]] = {
            "time": lightcurve["time"].mjd,
            "pitch": lightcurve["rate"].value,
        }

        # set 0 to 100 percentile limits so the full pitch range is used...
        # setting 0 to 105 for time means the sonification is 5% longer than
        # the time needed to trigger each note - by making this more than 100%
        # we give all the notes time to ring out (setting this at 100% means
        # the final note is triggered at the moment the sonification ends)
        lims: Dict[str, Tuple[str, str]] = {
            "time": ("0%", "105%"),
            "pitch": ("0%", "100%")
        }

        # set up source
        sources: Events = Events(maps.keys())
        sources.fromdict(maps)
        sources.apply_mapping_functions(map_lims=lims)

        return StraussSonification(score, sources, sampler, self.SYSTEM)

    @staticmethod
    def load_fixtures(
            session: Session,
            fixtures_path: Path = None,
    ) -> None:
        """
        Loads the fixtures from disk (if they aren't loaded already)

        Parameters
        ----------
        session: Session
            A database session to add the fixtures to.
        fixtures_path: Path
            The fixtures JSON file to load the fixtures from.

        Raises
        ------
        FileNotFoundError
            If the passed path (or the path in the config file) does not exist.
        ValueError
            If the file doesn't have the right columns.
        """
        if not fixtures_path:
            fixtures_path = Path(config_paths["soundfont_fixtures"])
            if not fixtures_path.exists():
                raise FileNotFoundError(f"The fixtures file '{fixtures_path}' does not exist.")

        # If there is at least one sonification method in the database, it is already defined
        if session.query(SonificationMethodSoundfont).first():
            # Using raise on a warning stops execution, unlike warnings.warn
            raise Warning("Soundfont Sonification Methods have already been imported")

        fixtures_df: DataFrame =read_csv(
            fixtures_path, skipinitialspace=True,
        )
        expected_columns: List[str] = SonificationMethod.COLUMNS + SonificationMethodSoundfont.COLUMNS
        if set(fixtures_df.columns) != set(expected_columns):
            raise ValueError(
                f"Expecting columns: {', '.join(expected_columns)}.\nGot: {', '.join(fixtures_df.columns)}.\n"
                f"Missing: {set(expected_columns) - set(fixtures_df.columns)}.\n"
                f"Extra: {set(fixtures_df.columns)- set(expected_columns)}."
            )

        for idx, row in fixtures_df.iterrows():
            session.add(
                SonificationMethodSoundfont(**row)
            )

        session.commit()
