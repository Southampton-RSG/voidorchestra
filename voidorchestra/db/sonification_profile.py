#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Defines the sonification profiles - a modification of a particular instrument.
"""
from csv import DictReader
from json import loads
from pathlib import Path
from typing import TYPE_CHECKING, List

from astropy.timeseries import TimeSeries
from sqlalchemy import Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship
from strauss.score import Score
from strauss.sonification import Sonification as StraussSonification

from voidorchestra import config_paths
from voidorchestra.db import Base

if TYPE_CHECKING:
    from voidorchestra.db import Sonification, SonificationMethod, SubjectSet


class SonificationProfile(Base):  # pylint: disable=too-few-public-methods
    """
    ORM class for sonification profiles.

    These are the patterns of sonification that are used to generate sonifications for data.
    They include an instrument, and how it is used.

    Attributes
    ----------
    id: integer
        A unique ID for the sonification profile.
    sonification_method_id: integer
        The ID of the sonification method used by this profile.
    name: string
        The name of the sonification profile.
    description: string
        A description of the sonification profile.
    tempo: float
        The speed of the sonification.
    key: text
        The note(s) to use for the sonification.
    sonification_method: relationship
        The method used to sonify data as part of this profile.
        Can be synthesizer or instrument samples.
    sonifications: relationship
        The sonifications generated using this profile.
    """
    __tablename__: str = "sonification_profile"

    id: Mapped[int] = mapped_column(primary_key=True)

    sonification_method_id: Mapped[int] = mapped_column(
        ForeignKey("sonification_method.id"),
    )
    name: Mapped[str] = mapped_column(String(32),nullable=False)
    description: Mapped[str] = mapped_column(String(256))
    tempo: Mapped[float] = mapped_column(Float())
    key: Mapped[str] = mapped_column(Text())

    sonifications: Mapped[List[Sonification]] = relationship(back_populates="sonification_profile")
    sonification_method: Mapped[SonificationMethod] = relationship(back_populates="sonification_profiles")
    subject_sets: Mapped[List[SubjectSet]] = relationship(back_populates="sonification_profile")

    COLUMNS: List[str] = [
        'id', 'sonification_method_id', 'tempo', 'key', 'name', 'description'
    ]

    __table_args__ = (
        UniqueConstraint(
            "sonification_method_id", "name", name="_sonification_profile_unique_modifier"),
    )

    def __repr__(self) -> str:
        return f"SonificationProfile(id={self.id}, name={self.sonification_method.name}: {self.name})"

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
            A database session to add the fixtures to
        fixtures_path: Path
            The fixtures JSON file to load the fixtures from

        Raises
        ------
        FileNotFoundError
            If the passed path (or the path in the config file) does not exist
        ValueError
            If the file doesn't have the right columns.
        """
        if not fixtures_path:
            fixtures_path = Path(config_paths["sonification_profile_fixtures"])
            if not fixtures_path.exists():
                raise FileNotFoundError(f"The fixtures file '{fixtures_path}' does not exist.")

        with open(fixtures_path, "r", encoding="utf-8") as fixtures_file:
            fixtures = DictReader(fixtures_file, skipinitialspace=True)
            expected_columns: List[str] = SonificationProfile.COLUMNS
            if fixtures.fieldnames != expected_columns:
                raise ValueError(
                    f"Expecting columns '{", ".join(expected_columns)}'.\n Got '{", ".join(fixtures.fieldnames)}'.\n"
                    f"Difference: {set(expected_columns).difference(set(fixtures.fieldnames))}."
                )

            for fixture in fixtures:
                session.add(
                    SonificationProfile(**fixture)
                )

        session.commit()

    def get_key(self) -> List[str]:
        """

        Returns
        -------

        """
        return loads(self.key)

    def create_sonification(
            self, lightcurve: TimeSeries
    ) -> StraussSonification:
        """

        Parameters
        ----------
        lightcurve: TimeSeries
            The lightcurve to sonify.

        Returns
        -------
        StraussSonification:
            The sonified lightcurve.
        """
        score: Score = Score(
            self.get_key(),
            len(lightcurve) / self.tempo,
        )
        return self.sonification_method.sonify_lightcurve(
            score, lightcurve
        )
