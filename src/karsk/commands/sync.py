from __future__ import annotations

import click
import asyncio
from pathlib import Path

from karsk.commands._common import (
    argument_areas_file,
    argument_config_file,
    option_staging,
)
from karsk.config import load_areas
from karsk.context import Context
from karsk.syncer import sync_all


@click.command("sync", help="Synchronise all locations")
@argument_config_file
@argument_areas_file
@option_staging
def subcommand_sync(config_file: Path, areas_file: Path, staging: Path) -> None:
    ctx = Context.from_config_file(config_file, staging=staging, engine="native")
    areas = load_areas(areas_file)
    asyncio.run(
        sync_all(
            ctx,
            areas=areas,
        )
    )
