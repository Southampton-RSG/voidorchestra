#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Defines the database object for Zooniverse subjects.

These are used to query the subjects which have been uploaded to the Zooniverse.
Can be used to filter subjects which are part of a certain subject set, workflow
or project.
"""
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.orm import Mapped, relationship, mapped_column, backref

from voidorchestra.db import Base

if TYPE_CHECKING:
    from voidorchestra.db import SubjectSet, Sonification, Classification


class Subject(Base):  # pylint: disable=too-few-public-methods
    """
    ORM class for subject sets.

    This class is used to query the subjects which have been uploaded and
    contains metadata about associations of the subject to projects, users
    and other structures in Zooniverse.

    Attributes
    ----------
    subject_id: integer
        The ID of the subject in the local DB
    zooniverse_subject_id: integer
        Foreign key, the ID of the subject this is
    retired: boolean
        Boolean flag to indicate if the subject has been retired due to a
        consensus being reached.
    zooniverse_workflow_id: integer
        The Zooniverse ID of the workflow the subject is assigned to.
    subject_set_id: integer
        Foreign key, the ID of the subject set the subject is assigned to
    zooniverse_subject_set_id: integer
        The Zooniverse ID of the subject set this is a subject of.

    classifications: relationship
        A relationship link to the classifications of this subject.
    subject_set: relationship
        A relationship link to the subject set.
    sonification: relationship
        A relationship link to the sonification.
    """
    __tablename__: str = "subject"

    id: Mapped[int] = mapped_column(primary_key=True)

    sonification_id: Mapped[int] = mapped_column(ForeignKey("sonification.id"), nullable=False)
    sonification: Mapped['Sonification'] = relationship(back_populates="subject", uselist=False)

    subject_set_id: Mapped[int] = mapped_column(ForeignKey("subject_set.id"), nullable=False)
    subject_set: Mapped['SubjectSet'] = relationship("SubjectSet", back_populates="subjects", uselist=False)

    classifications: Mapped[List['Classification']] = relationship(
        "Classification", back_populates="subject", uselist=True
    )

    zooniverse_project_id: Mapped[int] = mapped_column(Integer)
    zooniverse_subject_id: Mapped[int] = mapped_column(Integer)
    zooniverse_subject_set_id: Mapped[int] = mapped_column(Integer)
    zooniverse_workflow_id: Mapped[int] = mapped_column(Integer)

    retired: Mapped[bool] = mapped_column(Boolean)

    def __repr__(self) -> str:
        string = "Subject("
        string += f"subject_id={self.id!r} "
        string += f"subject_set_id={self.subject_set_id!r} "
        string += f"sonification_id={self.sonification_id!r}"
        string += ")"
        return string
