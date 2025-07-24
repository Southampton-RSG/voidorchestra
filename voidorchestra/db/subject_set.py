#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Defines the database object for Zooniverse subject sets.

These are used to store the active subject sets in a project and workflow.
"""
from typing import TYPE_CHECKING, List

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from voidorchestra.db import Base, LightcurveCollection

if TYPE_CHECKING:
    from voidorchestra.db.sonification_profile import SonificationProfile
    from voidorchestra.db.subject import Subject


class SubjectSet(Base):
    """
    ORM class for subject sets.

    This class is used to query subject sets which have been created and are
    in use by a project and workflow

    Attributes
    ----------
    id: integer
        Primary key.
    zooniverse_subject_set_id: integer
        The Zooniverse ID for the subject set, indexed.
    zooniverse_workflow_id: int
        The ID of the Zooniverse workflow the subject set is assigned to.
    display_name: string
        The display name of the subject set on the Zooniverse.
    subjects: relationship
        The subjects associated with the subject set.
    sonification_profile_id: integer
        The foreign key for the sonification profile used to generate the subjects in this set.
    sonification_profile: relationship
        The sonification profile used to generate the subjects in this set.
    """
    __tablename__: str = "subject_set"

    id: Mapped[int] = mapped_column(primary_key=True)
    lightcurve_collection_id: Mapped[int] = mapped_column(
        ForeignKey("lightcurve_collection.id")
    )
    sonification_profile_id: Mapped[int] = mapped_column(
        ForeignKey("sonification_profile.id")
    )
    zooniverse_subject_set_id: Mapped[int] = mapped_column(index=True)
    priority: Mapped[int] = mapped_column()
    display_name: Mapped[str] = mapped_column(String(256), unique=False)

    sonification_profile: Mapped['SonificationProfile'] = relationship(
        "SonificationProfile", back_populates="subject_sets",
    )
    lightcurve_collection: Mapped[LightcurveCollection] = relationship(
        "LightcurveCollection", back_populates="subject_sets",
    )
    subjects: Mapped[List['Subject']] = relationship(
        "Subject", back_populates="subject_set", uselist=True,
    )



