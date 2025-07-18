#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
Defines the sonifications used.
"""
from pathlib import Path
from uuid import uuid4

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from voidorchestra import config_paths
from voidorchestra.db import Base
from voidorchestra.db.lightcurve import Lightcurve  # noqa: F401
from voidorchestra.db.sonification_profile import SonificationProfile  # noqa: F401
from voidorchestra.db.subject import Subject  # noqa: F401


class Sonification(Base):  # pylint: disable=too-few-public-methods
    """
    ORM class for sonification files.

    This class bundles together the locations of the audio, video and image files,
    and links to the lightcurve and sonification profile used to generate them.

    Attributes
    ----------
    id: integer
        A unique ID for the sonification.
    uuid: string
        The UUID for the sonification files & URL.
    lightcurve: relationship
        The lightcurve this sonification was generated from.
    sonification_profile: relationship
        The sonification profile used to generate the lightcurve.
    subject: relationship
        The corresponding subject on Zooniverse.
    """
    __tablename__: str = "sonification"

    id: Mapped[int] = mapped_column(primary_key=True)
    sonification_profile_id: Mapped[int] = mapped_column(
        ForeignKey("sonification_profile.id"), nullable=False,
    )

    lightcurve_id: Mapped[int] = mapped_column(
        ForeignKey("lightcurve.lightcurve_id"), nullable=False,
    )

    uuid: Mapped[str] = mapped_column(String(32), unique=True)
    path_audio: Mapped[str] = mapped_column(String(128))
    path_video: Mapped[str] = mapped_column(String(128))
    path_image: Mapped[str] = mapped_column(String(128))
    processed: Mapped[bool] = mapped_column(Boolean(), default=False)
    figure: Mapped[bool] = mapped_column(Boolean(), default=True)

    confidence: Mapped[float] = mapped_column(Float(), nullable=True)

    subject: Mapped[Subject] = relationship(back_populates="sonification", uselist=False)
    lightcurve: Mapped[Lightcurve] = relationship(back_populates="sonifications")
    sonification_profile: Mapped[SonificationProfile] = relationship(back_populates="sonifications")

    def __repr__(self) -> str:
        return f"Sonification(id={self.id!r})"


def create_sonification(
        lightcurve: Lightcurve,
        sonification_profile: SonificationProfile,
) -> Sonification:
    """
    Creates a new sonification, including setting the UUID and paths.

    Required as SQLight/MySQL don't support the UUID column type.

    Parameters
    ----------
    lightcurve: Lightcurve
        The lightcurve this sonification was generated from.
    sonification_profile: SonificationProfile
        The sonification profile used to sonify the lightcurve.

    Returns
    -------
    Sonification:
        The sonification, with derived columns like UUID filled in.
    """
    sonification_uuid: str = str(uuid4())
    path_root: Path = config_paths["output"] / f"{sonification_uuid}-lightcurve-{lightcurve.id}-profile-{sonification_profile.id}"

    sonification: Sonification = Sonification(
        lightcurve=lightcurve,
        sonification_profile=sonification_profile,
        uuid=sonification_uuid,
        path_audio=str(path_root.with_suffix(".mp3")),
        path_video = str(path_root.with_suffix(".mp4")),
        path_image = str(path_root.with_suffix(".png")),
    )
    return sonification
