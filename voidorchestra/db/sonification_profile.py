#!/usr/bin/env python3
# -*- coding:utf-8 -*-

"""
Defines the patients.

Currently very minimal; patients are created as part of the batch upload process
"""

from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Boolean
from sqlalchemy import Enum
from sqlalchemy.orm import relationship

from voidorchestra.db import Base


class SonificationProfile(Base):  # pylint: disable=too-few-public-methods
    """
    ORM class for sonification profiles.

    These are the patterns of sonification that are used to generate sonifications for data.
    They include an instrument, and how it is used.

    Attributes
    ----------
    sonification_profile_id: integer
        A unique ID for the patient
    name: string
        The name of the sonification profile.
    description: string
        A description of the sonification profile.
    sonification_method: bool
        The method used to sonify data as part of this profile.
        Can be synthesizer or instrument samples.
    sonifications: relationship
        The sonifications generated using this profile.
    """
    __tablename__ = "sonification_profile"

    sonification_profile_id = Column("sonification_profile_id", Integer(), primary_key=True)
    name = Column("name", String(32), unique=True, nullable=False)
    description = Column("description", String(256))

    sonifications = relationship("Sonification", back_populates="sonification_profile")
    sonification_method = relationship("SonificationMethod", back_populates="sonification_profiles")

    def __repr__(self) -> str:
        return f"SonificationProfile(id={self.sonification_profile_id}, name={self.name})"
