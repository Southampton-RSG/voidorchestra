#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Defines the database object for sonification using synthesizers.
"""
from csv import DictReader
from json import loads
from pathlib import Path
from typing import Dict, List

from sqlalchemy import Column, Float
from sqlalchemy.orm import Session
from strauss.generator import Synthesizer
from strauss.sonification import Sonification

from voidorchestra import config_paths
from voidorchestra.db.sonification_method import SonificationMethod


class SonificationMethodSynthesizer(SonificationMethod):
    """
    Shared-table inheritance subclass for Synthesizer sonification methods.

    Attributes
    ----------
    pitch: float
        aaa
    pitch_shift_power: float
        Power of the pitch shift.
    length: float
        Duration of the sonification, in seconds.
    """
    pitch = Column("pitch", Float())
    pitch_shift_power = Column("pitch_shift_power", Float())
    length = Column("length", Float())

    COLUMNS: List[str] = [
        'pitch', 'pitch_shift_power', 'length'
    ]

    __mapper_args__: Dict[str, str] = {
        'polymorphic_identity': 'sonification_method_synthesizer',
    }

    def __repr__(self) -> str:
        return f"SonificationMethodSynthesizer(id={self.sonification_method_id!r})"

    def get_generator(self) -> Synthesizer:
        """
        Gets the generator used to sonify the data by this method.

        Returns
        -------
        Synthesizer:
            The sound generator.
        """
        synthesizer: Synthesizer = Synthesizer()
        preset: str|Dict = loads(self.preset)
        synthesizer.load_preset(preset)
        synthesizer.preset_details(preset)
        return synthesizer

    @staticmethod
    def load_fixtures(
            session: Session,
            fixtures_path: Path = None
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
            fixtures_path = Path(config_paths["synthesizer_fixtures"])
            if not fixtures_path.exists():
                raise FileNotFoundError(f"The fixtures file '{fixtures_path}' does not exist.")

        # If there is at least one sonification method in the database, it is already defined
        if session.query(SonificationMethodSynthesizer).first():
            # Using raise on a warning stops execution, unlike warnings.warn
            raise Warning("Synthesizer Sonification Methods have already been imported")

        with open(fixtures_path, "r", encoding="utf-8") as fixtures_file:
            fixtures: DictReader = DictReader(fixtures_file, skipinitialspace=True)
            expected_columns: List[str] = SonificationMethod.COLUMNS + SonificationMethodSynthesizer.COLUMNS
            if set(fixtures.fieldnames) != set(expected_columns):
                raise ValueError(
                    f"Expecting columns: {', '.join(expected_columns)}.\nGot: {', '.join(fixtures.fieldnames)}.\n"
                    f"Missing: {set(expected_columns) - set(fixtures.fieldnames)}.\n"
                    f"Extra: {set(fixtures.fieldnames)- set(expected_columns)}."
                )

            for fixture in fixtures:
                session.add(
                    SonificationMethodSynthesizer(**fixture)
                )

        session.commit()

    def sonify_lightcurve(self, generator: Synthesizer) -> Sonification:
        """

        Parameters
        ----------
        generator

        Returns
        -------
        Sonification:
            The sonified version of the lightcurve.
        """
