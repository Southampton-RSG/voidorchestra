#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Defines the database object for the lightcurve.

Uses single-table inheritance to contain multiple types of lightcurve.
"""
from typing import Dict, List

from astropy.timeseries import TimeSeries
from plotly.graph_objs import Figure
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from voidorchestra.db import Base


class Lightcurve(Base):  # pylint: disable=too-few-public-methods
    """
    ORM class for a lightcurve.

    This class defines a type of lightcurve.
    Multiple versions exist, for synthetic, observed, or input.

    Attributes
    ----------
    lightcurve_id: integer
        The lightcurve method id.
    polymorphic_type: str
        The column used for single-table polymorphism.
    sonifications: relationship
        The sonifications generated using this lightcurve.
    """
    __tablename__: str = "lightcurve"
    __mapper_args__: Dict[str, str] = {
        "polymorphic_on": "polymorphic_type",
    }

    lightcurve_id = Column("lightcurve_id", Integer, primary_key=True)
    polymorphic_type = Column("polymorphic_type", String(64))
    name = Column(
        "name", String(64), nullable=False
    )

    sonifications = relationship("Sonification", back_populates="lightcurve")

    COLUMNS: List[str] = [
        'lightcurve_id'
    ]

    def __repr__(self) -> str:
        """
        Gets the name of the lightcurve.

        Returns
        -------
        str:
            The string representation of the lightcurve.
        """
        raise NotImplementedError("This is an abstract class")

    def get_data(
            self,
            **kwargs,
    ) -> TimeSeries:
        """
        Gets a table containing the lightcurve.

        Returns
        -------
        TimeSeries:
            The Astropy TimeSeries representing the lightcurve.
            Must have time, rate and error columns.
        """
        raise NotImplementedError("This is an abstract method.")
