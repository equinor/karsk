from __future__ import annotations

import io
import os
import shlex
import subprocess
import sys
import asyncio
from pathlib import Path

from karsk.config import AreaConfig
from karsk.context import Context
from karsk.utils import redirect_output


_RSH: list[str] = [
    "ssh",
    "-q",
    "-oBatchMode=yes",
    "-oPasswordAuthentication=no",
    "-oStrictHostKeyChecking=no",
    "-oConnectTimeout=20",
]


_DEFAULT_UNAME = "x86_64 GNU/Linux"


def _make_pre_script(ctx: Context, uname: str) -> str:
    """Bash script that will run before 'rsync'"""
    return "".join(
        (
            "set -euxo pipefail\n",
            f"test \"$(uname -mo)\" = '{uname}'\n",
            f"mkdir -p {ctx.destination_paths.store}\n",
            f"mkdir -p {ctx.destination_paths.versions}\n",
        )
    )


def _make_post_script(ctx: Context) -> str:
    """Bash script that will run after 'rsync'"""
    script = io.StringIO()
    script.write("set -euxo pipefail\n")
    script.writelines(
        f"ln -sfn {os.readlink(path)} {path} \n"
        for path in ctx.destination_paths.versions.glob("*")
        if path.is_symlink()
        if (path / "manifest").is_file()
    )
    return script.getvalue()


class Sync:
    def __init__(
        self,
        ctx: Context,
        *,
        dry_run: bool = False,
    ) -> None:
        self._dry_run: bool = dry_run

        self._store_paths: list[Path] = [
            ctx.out_destination(pkg) for pkg in ctx.packages.values()
        ]

        self._env_paths: list[Path] = [
            path.parent
            for path in ctx.destination_paths.versions.glob("*/manifest")
            if not path.parent.is_symlink()
            if ctx.packages[ctx.config.main_package].manifest == path.read_text()
        ]


async def _sync_to(
    ctx: Context,
    store_paths: list[Path],
    version_paths: list[Path],
    area: AreaConfig,
    uname: str,
) -> None:
    # Ensure directories are created
    await _bash(area, _make_pre_script(ctx, uname), context="prescript")

    # 2. Sync store/
    await _rsync(
        area,
        store_paths,
        ctx.destination_paths.store,
        context="store",
    )

    # 3. Sync versions (eg. versions/1.0.2+2)
    await _rsync(
        area,
        version_paths,
        ctx.destination_paths.versions,
        context="versions",
    )

    # 4. Sync versions (eg. versions/1.0.2+2)
    await _rsync(
        area,
        [ctx.destination_paths.bin],
        ctx.destination_paths.bin.parent,
        context="versions",
    )

    # 5. Sync all symlinks
    await _bash(area, _make_post_script(ctx), context="symlinks")


async def _bash(area: AreaConfig, script: str, *, context: str | None = None) -> None:
    await _check_call(
        area,
        *_RSH,
        area.host,
        "bash",
        input=script,
        context=context,
    )


async def _rsync(
    area: AreaConfig,
    paths: list[Path],
    parent: Path,
    *,
    context: str | None = None,
) -> None:
    await _check_call(
        area,
        "rsync",
        "-a",
        "--rsh",
        shlex.join(_RSH),
        "--progress",
        *paths,
        f"{area.host}:{parent}",
        context=context,
    )


async def _check_call(
    area: AreaConfig,
    program: str | Path,
    *args: str | Path,
    input: str | None = None,
    context: str | None = None,
    dry_run: bool = False,
) -> None:
    if dry_run:
        print(f"{(program, *args)}", f"{input=}")
        return

    proc = await asyncio.create_subprocess_exec(
        program,
        *args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )

    if proc.stdin is None:
        raise RuntimeError("Process stdin is None despite PIPE being requested")
    if input is not None:
        proc.stdin.write(input.encode())
    proc.stdin.close()

    stdout = io.StringIO()
    stderr = io.StringIO()

    returncode, _, _ = await asyncio.gather(
        proc.wait(),
        redirect_output(
            f"{area.name} {repr(context)}", proc.stdout, sys.stdout, stdout
        ),
        redirect_output(
            f"{area.name} {repr(context)}", proc.stderr, sys.stderr, stderr
        ),
    )

    if returncode != 0:
        raise subprocess.CalledProcessError(
            returncode, (program, *args), stdout.getvalue(), stderr.getvalue()
        )


async def sync_all(
    ctx: Context,
    areas: list[AreaConfig],
    *,
    uname: str = _DEFAULT_UNAME,
) -> None:
    store_paths = [ctx.out_destination(pkg) for pkg in ctx.packages.values()]

    version_paths = [
        path.parent
        for path in ctx.destination_paths.versions.glob("*/manifest")
        if not path.parent.is_symlink()
        if ctx.packages[ctx.config.main_package].manifest == path.read_text()
    ]

    results = await asyncio.gather(
        *(
            _sync_to(
                ctx,
                store_paths,
                version_paths,
                area,
                uname,
            )
            for area in areas
        ),
        return_exceptions=True,
    )
    for index, result in enumerate(results):
        if not isinstance(result, BaseException):
            continue
        print(f"During syncing to {areas[index].name}:")
        raise result
