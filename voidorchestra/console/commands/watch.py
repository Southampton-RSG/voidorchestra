#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This module contains sub-commands for `molegazer watch`.

The commands should watch directories for changes.
"""
import time
from typing import Optional

import click
import watchdog.events
import watchdog.observers

from voidorchestra import config


@click.group()
def watch():
    """Watch directories for new input data"""


@watch.command(
    name="images",
    help="Inputs the files in the config file's PATHS:images_new directory into the database."
)
@click.pass_context
@click.option(
    "-d",
    "--directory",
    nargs=1,
    type=click.Path(dir_okay=True, exists=True),
    default=None,
    help="An optional path to the directory to watch."
)
def watch_images(ctx: dict, directory: Optional[str] = None) -> None:
    """
    Watch for new files and upload them to the DB.

    Inputs the files in the config file's PATHS:images_new directory into the database.

    Parameters
    ----------
    directory: Optional[str]
        If provided, a directory to watch for new files in (that is not the default one)
    """
    if not directory:
        directory = config['PATHS']['images_new']
    elif directory == config['PATHS']['images_new']:
        click.echo(
            "Warning: Directory passed with `-d` is the same as the default directory!"
        )

    class OnCreatedEvent(watchdog.events.LoggingEventHandler):
        """
        Class that provides functions that are triggered when specific events occur.
        """
        def on_created(self, event: watchdog.events.FileSystemEvent):
            """
            Triggered when a file is created, prompts an upload of the images.

            Parameters
            ----------
            event: FileSystemEvent
                The event that has happened, including details on file path etc.
            """
            upload_images(directory)

    event_handler: OnCreatedEvent = OnCreatedEvent()
    observer = watchdog.observers.Observer()
    observer.schedule(event_handler, directory, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

    if ctx.obj["VERBOSE"] or ctx.obj["DEBUG"]:
        click.echo("Imported image files")
