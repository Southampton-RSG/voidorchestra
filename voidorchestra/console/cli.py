#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Entry point for the `void-orchestra` command.
"""

from logging import DEBUG, INFO

import click

from voidorchestra import log
from voidorchestra.console.commands.add import add
from voidorchestra.console.commands.admin import admin
from voidorchestra.console.commands.check import check
from voidorchestra.console.commands.clear import clear
from voidorchestra.console.commands.create import create
from voidorchestra.console.commands.init import init
from voidorchestra.console.commands.remove import remove
from voidorchestra.console.commands.sync import sync
from voidorchestra.console.commands.upload import upload
from voidorchestra.console.commands.watch import watch


@click.group()
@click.option(
    "-cm", "--commit_freq", 
    nargs=1, type=int, default=500, help="The frequency to commit changes"
)
@click.option(
    "-v", "--verbose", 
    flag_value=True, type=bool, help="Enable verbose output"
)
@click.option(
    "-vv", "--debug", 
    flag_value=True, type=bool, help="Enable debug output"
)
@click.pass_context
def cli(
        ctx: click.Context, verbose: bool, commit_freq: int, debug: bool
) -> None:
    """
    Void Orchestra Conductor.

    The purpose of this program is to provide an easy to use set of commands
    which allow you to create sonifications of QPO data, and link them to the Zooniverse.
    """
    ctx.ensure_object(dict)
    ctx.obj["COMMIT_FREQUENCY"] = commit_freq
    ctx.obj["VERBOSE"] = verbose
    ctx.obj["DEBUG"] = debug

    if verbose:
        log.set_logger_levels(INFO)
    if debug:
        log.set_logger_levels(DEBUG)



cli.add_command(init)

cli.add_command(add)
cli.add_command(upload)
cli.add_command(clear)
cli.add_command(create)
cli.add_command(watch)
cli.add_command(remove)

cli.add_command(admin)
cli.add_command(sync)
cli.add_command(check)