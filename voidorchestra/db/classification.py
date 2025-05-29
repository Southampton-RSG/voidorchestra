#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Defines the database object for Zooniverse subject classifications.
"""
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Column
from sqlalchemy import ForeignKey

from sqlalchemy.orm import relationship

from voidorchestra.db import Base


class Classification(Base):  # pylint: disable=too-few-public-methods
    """
    ORM class for image classifications.

    This class is used to query classifications of sonifications.

    Attributes
    ----------
    classification_id : Integer
        Caesar reduction/classification ID.
    subject_id : Integer
        Foreign key, the Zooniverse ID for the subject this
        classification is for.
    subject:  relationship
        A relationship link to the subject
    """
    __tablename__ = "classification"

    classification_id = Column("classification_id", Integer, primary_key=True, autoincrement=True)
    zooniverse_classification_id = Column("zooniverse_classification_id", Integer)

    subject_id = Column("subject_id", Integer, ForeignKey("subject.subject_id"), nullable=False)
    subject = relationship("Subject", back_populates="classifications")

    def __repr__(self) -> str:
        string = "Classification("
        string += f"classification_id={self.classification_id!r} "
        string += ")"
        return string
