#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Defines the database object for sonification methods.

Uses single-table inheritance to contain multiple types of sonification method.
"""
from typing import Dict, List

from astropy.timeseries import TimeSeries
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship
from strauss.score import Score
from strauss.sonification import Sonification as StraussSonification

from voidorchestra.db import Base


class SonificationMethod(Base):  # pylint: disable=too-few-public-methods
    """
    ORM class for sonification methods.

    This class defines a way that data is converted into sound files.
    Multiple versions exist, for using sound samples or using a synthesiser.

    Attributes
    ----------
    id: integer
        The sonification method id.
    name: str
        The name of the method.
    polymorphic_type: str
        The column used for single-table polymorphism.
    preset: str
        A preset definition for the method.
    sonification_profiles: relationship
        The sonification profiles using this method.
    """
    __tablename__: str = "sonification_method"
    __mapper_args__: Dict[str, str] = {
        "polymorphic_on": "polymorphic_type",
    }

    id = Column("id", Integer, primary_key=True)
    name = Column("name", String(32), unique=True, nullable=False)
    description = Column("description", Text())

    preset = Column("preset", Text())

    polymorphic_type = Column("polymorphic_type", String(64))

    sonification_profiles = relationship("SonificationProfile", back_populates="sonification_method")

    COLUMNS: List[str] = [
        'sonification_method_id', 'name', 'description', 'preset'
    ]

    def __repr__(self) -> str:
        """
        Gets the name of the sonification method.\

        Returns
        -------
        str:
            The string representation of the sonificaiton method..
        """
        raise NotImplementedError("This is an abstract class")

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
        raise NotImplementedError("This is an abstract method.")
