#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Defines the database object for the lightcurve.

Uses single-table inheritance to contain multiple types of lightcurve.
"""

from typing import TYPE_CHECKING, Dict, List

from astropy.timeseries import TimeSeries
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from voidorchestra.db import Base
from voidorchestra.db.lightcurve_collection import LightcurveCollection

if TYPE_CHECKING:
    from voidorchestra.db.sonification import Sonification


class Lightcurve(Base):  # pylint: disable=too-few-public-methods
    """
    ORM class for a lightcurve.

    This class defines a type of lightcurve.
    Multiple versions exist, for synthetic, observed, or input.

    Attributes
    ----------
    id: integer
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

    id: Mapped[int] = mapped_column(primary_key=True)
    polymorphic_type: Mapped[str] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(64), nullable=True)
    lightcurve_collection_id: Mapped[LightcurveCollection] = mapped_column(
        ForeignKey("lightcurve_collection.id"),
    )

    lightcurve_collection: Mapped[LightcurveCollection] = relationship(
        "LightcurveCollection",
        back_populates="lightcurves",
    )
    sonifications: Mapped[List["Sonification"]] = relationship(
        "Sonification",
        uselist=True,
        back_populates="lightcurve",
    )

    COLUMNS: List[str] = ["id", "name"]

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
