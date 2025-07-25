#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains sub-commands for `voidorchestra create`.

These are commands that create files using entities already in the database, e.g. the sonifications.
"""

import click

from voidorchestra.console.commands.create.sonifications import create_sonifications


@click.group()
def create():
    """
    Create entities within the database
    """


create.add_command(create_sonifications)
