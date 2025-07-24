#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Defines the QPO models, made up of components, used in synthetic lightcurve generation.
"""
from typing import TYPE_CHECKING, List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from voidorchestra.db import Base

if TYPE_CHECKING:
    from voidorchestra.db.lightcurve import Lightcurve
    from voidorchestra.db.subject_set import SubjectSet


class LightcurveCollection(Base):
    """
    ORM class for a collection of lightcurves in a batch.

    Attributes
    ----------
    id: integer
        A unique ID for the QPO model.
    name: string
        A name describing the batch.
    """
    __tablename__: str = "lightcurve_collection"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(32))

    lightcurves: Mapped[List['Lightcurve']] = relationship(
        back_populates="lightcurve_collection", uselist=True
    )
    subject_sets: Mapped['SubjectSet'] = relationship(
        back_populates="lightcurve_collection", uselist=True
    )

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r}, name={self.name!r})"
