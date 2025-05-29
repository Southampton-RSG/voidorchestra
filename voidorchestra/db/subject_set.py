#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Defines the database object for Zooniverse subject sets.

These are used to store the active subject sets in a project and workflow.
"""
from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.orm import validates, relationship, backref

from voidorchestra.db import Base


class SubjectSet(Base):  # pylint: disable=too-few-public-methods
    """
    ORM class for subject sets.

    This class is used to query subject sets which have been created and are
    in use by a project and workflow

    Attributes
    ----------
    subject_set_id: integer
        Primary key.
    zooniverse_subject_set_id: integer
        The Zooniverse ID for the subject set, indexed.
    zooniverse_workflow_id: int
        The ID of the Zooniverse workflow the subject set is assigned to.
    display_name: string
        The display name of the subject set on the Zooniverse.
    subjects: relationship
        The subjects associated with the subject set.
    sonification_profile: relationship
        The sonification profile used to generate the subjects in this set.
    """
    __tablename__ = "subject_set"

    subject_set_id = Column("subject_set_id", Integer, primary_key=True, autoincrement=True)
    subjects = relationship("Subject", back_populates="subject_set")

    zooniverse_subject_set_id = Column("zooniverse_subject_set_id", Integer, index=True)
    zooniverse_workflow_id = Column("zooniverse_workflow_id", Integer, index=True)

    display_name = Column("display_name", String(256))

    sonification_method_id = Column(
        "sonification_profile_id", Integer,
        ForeignKey("sonification_profile.sonification_profile_id")
    )
    sonification_method = relationship("Sonification", back_populates="subject_set")
