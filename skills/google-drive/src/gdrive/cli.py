"""CLI entrypoint -- registers all commands."""

from __future__ import annotations

import click

from gdrive.auth import auth
from gdrive.config import config
from gdrive.cp import cp
from gdrive.doctor import doctor
from gdrive.link import link
from gdrive.ls import ls
from gdrive.mkdir import mkdir
from gdrive.mv import mv
from gdrive.open import open_cmd
from gdrive.pull import pull
from gdrive.push import push
from gdrive.rm import rm
from gdrive.search import search
from gdrive.share import share
from gdrive.status import status
from gdrive.untrack import untrack


@click.group()
@click.version_option(package_name="gdrive")
def cli():
    """Google Drive CLI -- manifest-tracked push/pull via rclone."""


cli.add_command(auth)
cli.add_command(config)
cli.add_command(cp)
cli.add_command(doctor)
cli.add_command(link)
cli.add_command(ls)
cli.add_command(mkdir)
cli.add_command(mv)
cli.add_command(open_cmd, "open")
cli.add_command(pull)
cli.add_command(push)
cli.add_command(rm)
cli.add_command(search)
cli.add_command(share)
cli.add_command(status)
cli.add_command(untrack)
