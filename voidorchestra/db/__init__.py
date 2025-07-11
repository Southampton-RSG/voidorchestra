#!/usr/bin/env python3
# -*- coding:utf-8 -*-
"""
The Void Orchestra package contains ORM items based off of those in MoleGazer,
which allow creating sonifications of synthetic data and synchronising them to Zooniverse.
"""
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, declarative_base

Base: DeclarativeBase = declarative_base()

ENGINE: Engine|None = None

# Public functions -------------------------------------------------------------
from voidorchestra.db.classification import Classification  # noqa: E402
from voidorchestra.db.lightcurve import Lightcurve  # noqa: E402
from voidorchestra.db.lightcurve.synthetic import LightcurveSynthetic, LightcurveSyntheticRegular  # noqa: E402
from voidorchestra.db.qpo_model import QPOModel, QPOModelBPL, QPOModelComposite, QPOModelLorentzian, QPOModelSHO  # noqa: E402
from voidorchestra.db.sonification import Sonification  # noqa: E402
from voidorchestra.db.sonification_method import SonificationMethod  # noqa: E402
from voidorchestra.db.sonification_method.soundfont import SonificationMethodSoundfont  # noqa: E402
from voidorchestra.db.sonification_method.synthesizer import SonificationMethodSynthesizer  # noqa: E402
from voidorchestra.db.sonification_profile import SonificationProfile  # noqa: E402
from voidorchestra.db.subject import Subject  # noqa: E402
from voidorchestra.db.subject_set import SubjectSet  # noqa: E402


def create_database_tables(engine: Engine) -> None:
    """
    Create the database tables.

    Creates all the (or the missing) database tables. These tables are
    defined in each ORM class in the :code:`__tablename__` variable.

    Parameters
    ----------
    engine: Engine
        The engine to connection to the database.
    """
    Base.metadata.create_all(engine)


def create_new_database(location: Optional[str]) -> Engine:
    """
    Create the MoleMarshal database.

    Parameters
    ----------
    location : str
        The filepath to the database to create.

    Returns
    -------
    engine: sqlalchemy.Engine
        the database Engine object.
    """
    path: Path = Path(location)

    if path.suffix != ".db":
        location = str(path.with_suffix(".db"))

    engine = create_engine(f"sqlite+pysqlite:///{location}")
    create_database_tables(engine)

    return engine


def connect_to_database_engine(location: str) -> Engine:
    """
    Create a connection to the database.

    Return an SQLAlchemy Engine which creates a connection to the
    database. If the database does not exist, a new database is created. In
    the case of multiple calls of this function, a new engine will not be
    created and an already existing engine will be returned.

    Parameters
    ----------
    location : str
        The filepath to the database to open.

    Returns
    -------
    engine : sqlalchemy.engine
        The engine object to connect to the database.
    """
    global ENGINE  # pylint: disable=global-statement

    if ENGINE:
        return ENGINE

    path: Path  = Path(location)

    if not path.exists():
        raise OSError(f"Unable to open {location} as it doesn't exist")

    ENGINE = create_engine(f"sqlite+pysqlite:///{location}")

    return ENGINE


def commit_database(session: Session) -> None:
    """
    Commit changes to the database.

    Any changes queued up in the session will be committed, and appropriate
    messages will be sent to the logger.

    Parameters
    ----------
    session: Session
        The database session.
    """
    session.commit()
