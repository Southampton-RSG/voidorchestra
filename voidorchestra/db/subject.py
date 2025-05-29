#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Defines the database object for Zooniverse subjects.

These are used to query the subjects which have been uploaded to the Zooniverse.
Can be used to filter subjects which are part of a certain subject set, workflow
or project.
"""
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import Boolean
from sqlalchemy import ForeignKey

from sqlalchemy.orm import relationship

from voidorchestra.db import Base


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

    classification: relationship
        A relationship link to the classification.
    subject_set: relationship
        A relationship link to the subject set.
    sonification: relationship
        A relationship link to the sonification.
    """
    __tablename__ = "subject"

    subject_id = Column("id", Integer, primary_key=True, autoincrement=True)

    sonification_id = Column("sonification_id", Integer, ForeignKey("sonification.sonification_id"))
    sonification = relationship("Sonification", back_populates="subject")

    subject_set_id = Column("subject_set_id", Integer, ForeignKey("subject_set.subject_set_id"))
    subject_set = relationship("SubjectSet", back_populates="subject")

    classifications = relationship("Classification", back_populates="subject")

    zooniverse_subject_id = Column("zooniverse_subject_id", Integer)
    zooniverse_subject_set_id = Column("zooniverse_subject_set_id", Integer)
    zooniverse_workflow_id = Column("zooniverse_workflow_id", Integer)

    retired = Column("retired", Boolean)

    def __repr__(self) -> str:
        string = "Subject("
        string += f"subject_id={self.subject_id!r} "
        string += f"subject_set_id={self.subject_set_id!r} "
        string += f"sonification_id={self.sonification_id!r}"
        string += ")"
        return string
