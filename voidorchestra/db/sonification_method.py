#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Defines the database object for sonification methods.

Uses single-table inheritance to contain multiple types of sonification method.
"""
from csv import DictReader
from pathlib import Path
from typing import List, Tuple

from sqlalchemy import String, Text, Boolean, Integer, Column, ForeignKey
from sqlalchemy.orm import relationship

from voidorchestra import config
from voidorchestra.db import Base, Session


class SonificationMethod(Base):  # pylint: disable=too-few-public-methods
    """
    ORM class for sonification methods.

    This class defines a way that data is converted into sound files.
    Multiple versions exist, for using sound samples or using a synthesiser.

    Attributes
    ----------
    sonification_method_id: integer
        The sonification method id.
    name: str
        The name of the method.
    polymorphic_type: str
        The column used for single-table polymorphism.
    sonification_profiles: relationship
        The sonification profiles using this method.
    """
    __tablename__ = "sonification_method"

    sonification_method_id = Column("sonification_method_id", Integer, primary_key=True)
    name = Column("name", String(32), unique=True, nullable=False)
    description = Column("description", Text())

    polymorphic_type = Column("polymorphic_type", String(64))

    sonification_profiles = relationship("SonificationProfile", back_populates="sonification_method")

    COLUMNS = [
        'sonification_method_id', 'name', 'description'
    ]

    def __repr__(self) -> str:
        return f"SonificationMethod(id={self.sonification_method_id!r})"

class SonificationMethodSoundfont(SonificationMethod):
    """

    """
    preset = Column("preset", Text(), nullable=False)
    preset_modification = Column("preset_modification", Text())
    filepath = Column("filepath", String(256), nullable=False)
    continuous = Column("continuous", Boolean(), nullable=False)

    COLUMNS = [
        'preset', 'preset_modification', 'filepath', 'continuous'
    ]

    __mapper_args__ = {
        'polymorphic_identity': 'sonification_method_soundfont',
        'polymorphic_on': 'polymorphic_type',
    }


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
            A database session to add the fixtures to
        fixtures_path: Path
            The fixtures JSON file to load the fixtures from

        Raises
        ------
        FileNotFoundError
            If the passed path (or the path in the config file) does not exist

        """
        if not fixtures_path:
            fixtures_path = Path(config["PATHS"]["views"])
            if not fixtures_path.exists():
                raise FileNotFoundError(f"The fixtures file '{fixtures_path}' does not exist.")

        # If there is at least one sonification method in the database, it is already defined
        if session.query(SonificationMethod).first():
            # Using raise on a warning stops execution, unlike warnings.warn
            raise Warning("Sonification Methods have already been imported")

        with open(fixtures_path, "r", encoding="utf-8") as fixtures_file:
            fixtures = DictReader(fixtures_file, skipinitialspace=True)
            expected_columns: List[str] = SonificationMethod.COLUMNS + SonificationMethod.COLUMNS
            if fixtures.fieldnames != expected_columns:
                raise ValueError(
                    f"Expecting columns '{",".join(expected_columns)}' - got '{fixtures.fieldnames}'"
                )

            for fixture in fixtures:
                session.add(
                    SonificationMethodSoundfont(
                        sonification_method_id=fixture["id"],
                        name=fixture["name"],
                        description=fixture["description"],
                        preset=fixture["preset"],
                        preset_modification=fixture["preset_modification"],
                        continuous=fixture["continuous"],
                        filepath=fixture["filepath"],
                    )
                )

        session.commit()
