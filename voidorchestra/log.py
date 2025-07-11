#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The logger module contains the functions required to initialise a new or
retrieve an already existing logger, and to set the loggers across the entire
Void Orchestra package.
"""
from logging import INFO, WARNING, Formatter, Logger, StreamHandler, getLogger
from pkgutil import iter_modules
from types import ModuleType
from typing import List

import voidorchestra
import voidorchestra.process
import voidorchestra.process.sonification
import voidorchestra.zooniverse


# Classes ----------------------------------------------------------------------
class __VariableFormatter(Formatter):
    """
    Enable variable formatting depending on the logging level number.

    For INFO logs, only the message is printed. For any other level of logging,
    more verbose log output is used.
    """
    def format(self, record):
        if record.levelno == INFO:
            formatter: Formatter = Formatter("%(message)s")
        else:
            formatter: Formatter = Formatter(
                "[%(asctime)s] %(levelname)8s : %(message)s (%(filename)s:%(lineno)d)",
                "%Y-%m-%d %H:%M:%S",
            )
        return formatter.format(record)


# Private functions ------------------------------------------------------------
def __list_module_names_in_packages(
        packages: List[ModuleType]
) -> List[str]:
    """
    Get the names of the submodules in a module.

    Parameters
    ----------
    packages: List[ModuleType]
        The modules to find the submodules for.

    Returns
    -------
    submodule_names: List[str]
        A list of the submodule name.
    """
    submodule_names = []

    for package in packages:
        for submodule in iter_modules(package.__path__):
            if submodule.ispkg:
                continue
            submodule_names.append(f"{package.__name__}.{submodule.name}")

    return submodule_names


# Public functions -------------------------------------------------------------
def get_logger(
        logger_name: str
) -> Logger:
    """
    Initialize logging.

    This sets the stream, formatting for the logger and the verbosity level.
    The verbosity level is controlled by command line arguments, --verbose and
    --debug respectively.

    Parameters
    ----------
    logger_name: str
        The name of the logger instance.

    Returns
    -------
    new_logger: logging.Logger
        The new logging object, with the given name `logger_name`.
    """
    handler: StreamHandler = StreamHandler()
    handler.setFormatter(__VariableFormatter())

    new_logger: Logger = getLogger(logger_name)
    new_logger.addHandler(handler)
    new_logger.setLevel(WARNING)
    new_logger.propagate = False

    return new_logger


logger = get_logger(__name__.replace(".", "-"))


def set_logger_levels(level: int) -> None:
    """
    Set the level for all the loggers in Zooniverse Orchestrator.

    Parameters
    ----------
    level: int
        The logging level to set. Usually something like logging.WARNING, etc.
    """
    module_names: List[str] = __list_module_names_in_packages(
        [
            voidorchestra,
            voidorchestra.process,
            voidorchestra.process.sonification,
            voidorchestra.zooniverse,
        ]
    )

    for module in module_names:
        module_logger: Logger = getLogger(module.replace(".", "-"))
        module_logger.setLevel(level)
