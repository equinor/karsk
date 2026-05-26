from __future__ import annotations
import asyncio
from asyncio.subprocess import DEVNULL, PIPE
from contextlib import suppress
from datetime import datetime
import io
from itertools import chain
import os
from pathlib import Path
import shutil
import sys
from tempfile import NamedTemporaryFile, TemporaryDirectory

from karsk.console import console
from karsk.context import Context
from karsk.engine import VolumeBind
from karsk.fetchers import fetch_single
from karsk.links import make_links
from karsk.package import Package
from karsk.paths import Paths
from karsk.utils import redirect_output
from karsk.wrapper import install_wrapper


async def _async_build(
    ctx: Context,
    pkg: Package,
    env: dict[str, str],
    buildlog: io.TextIOWrapper,
    volumes: list[VolumeBind],
    cwd: Path,
) -> bool:
    tmpfile = NamedTemporaryFile(mode="w", prefix="karsk-builder", delete=False)
    tmpfile.writelines(
        [
            "#!/usr/bin/env bash\n",
            'echo "src: $src"\n',
            'echo "out: $out"\n',
            "echo\n",
            *(f'echo "{x}: ${x}"\n' for x in env.keys() if x not in ("src", "out")),
            "set -eux -o pipefail\n",
            pkg.config.build,
        ]
    )
    os.chmod(tmpfile.name, 0o777)
    tmpfile.close()

    volumes.append((tmpfile.name, tmpfile.name, "ro"))

    console.log("Mounting volumes:")
    for index, (src, dst, mode) in enumerate(volumes):
        console.log(f"{index + 1}. {dst} (host: {src}) as {mode}")

    proc = await ctx.engine(
        pkg.build_image,
        tmpfile.name,
        env=env,
        cwd=cwd,
        volumes=volumes,
        stdin=DEVNULL,
        stdout=PIPE,
        stderr=PIPE,
    )

    returncode, _, _ = await asyncio.gather(
        proc.wait(),
        redirect_output(pkg.config.name, proc.stdout, sys.stdout, buildlog),
        redirect_output(pkg.config.name, proc.stderr, sys.stderr, buildlog),
    )

    if returncode == 0:
        return True

    if ctx.can_debug:
        console.log(
            f"Failure during building of {pkg.fullname} (Returncode: {returncode})"
        )
        console.log("Entering interactive environment")
        console.log("$src: source for this package")
        console.log("$out: output path")
        for p in pkg.depends:
            console.log(f"${p.config.name} - output of dependency {p.fullname}")
        proc = await ctx.engine(
            pkg.build_image,
            "bash",
            env=env,
            cwd=cwd,
            volumes=volumes,
            terminal=True,
        )

        await proc.wait()

    return False


async def _build(ctx: Context, pkg: Package, tmp: str) -> None:
    if ctx.exists(pkg):
        console.log(
            f"Ignoring {pkg.fullname}: Already built at {ctx.out_any(pkg)}",
        )
        return

    out = ctx.out_staging(pkg)

    if ctx.engine.name == "native":
        # We use the target path in native mode. If an error occurs during
        # building, the bad build will stay and will result in a bad
        # installation. This is OK because 'native' is only used in tests.
        tmp_out = ctx.out_staging(pkg)
    else:
        tmp_out = ctx.staging_paths.builds / pkg.config.name
    shutil.rmtree(tmp_out, ignore_errors=True)
    tmp_out.mkdir(parents=True, exist_ok=False)

    src = ctx.staging_paths.src(pkg)

    print(f"Building {pkg.fullname}...")
    try:
        await fetch_single(ctx, pkg)
    except (Exception, KeyboardInterrupt):
        if src is not None:
            shutil.rmtree(src)
        raise

    env, volumes, cwd = _prepare_build_env(ctx, pkg, src, tmp_out, tmp)

    with open(tmp_out / "build.log", "w") as buildlog:
        print("Built with https://github.com/equinor/karsk", file=buildlog)
        print(f"Build date: {datetime.now()}", file=buildlog)
        print("----- BUILD CONFIG -----", file=buildlog)
        print(pkg.config.model_dump_json(), file=buildlog)
        print("------ BUILD  LOG ------", file=buildlog)

        if await _async_build(ctx, pkg, env, buildlog, volumes, cwd):
            shutil.move(tmp_out, out)
        else:
            sys.exit(f"Building {pkg.fullname} failed. Inspect the build at: {tmp_out}")


def _prepare_build_env(
    ctx: Context, pkg: Package, src: Path | None, tmp_out: Path, tmp: str
) -> tuple[dict[str, str], list[VolumeBind], Path]:
    env = {
        **{x.config.name: str(ctx.out_destination(x)) for x in pkg.depends},
        "tmp": tmp,
        "out": str(ctx.out_destination(pkg)),
        "CFLAGS": "-O3",
        "CXXFLAGS": "-O3",
        "FOPTFLAGS": "-O3",
        "MAKEFLAGS": "-j10",
    }

    volumes: list[VolumeBind] = [
        (ctx.out_any(x), ctx.out_destination(x), "ro") for x in pkg.depends
    ]
    if src is not None:
        env["src"] = (
            str(src) if ctx.engine.name == "native" else f"/tmp/pkgsrc/{src.name}"
        )

    cwd = Path("/tmp")
    if src is not None and src.is_dir():
        if ctx.engine.name == "native":
            cwd = src
        else:
            volumes.append((src, f"/tmp/pkgsrc/{src.name}", "rw"))
            cwd = Path("/tmp/pkgsrc") / src.name
    elif src is not None and ctx.engine.name != "native":
        volumes.append((src, f"/tmp/pkgsrc/{src.name}", "ro"))

    volumes.append((tmp_out, ctx.out_destination(pkg), "rw"))

    return env, volumes, cwd


async def _build_packages(ctx: Context, stop_after: Package | None = None) -> None:
    for pkg in ctx.packages.values():
        with TemporaryDirectory() as tmp:
            await _build(ctx, pkg, tmp)
        if pkg is stop_after:
            console.log(f"Stopping after {pkg.config.name} as requested")
            break


async def _build_envs(
    ctx: Context,
    paths: Paths,
    *,
    staging: bool,
) -> None:
    pkg = ctx.packages[ctx.config.main_package]
    env_path = _get_versions_path(paths, pkg)
    if env_path is not None:
        _build_env_for_package(ctx, env_path, pkg, staging=staging)

    default_links: dict[str, str] = {"latest": "^", "stable": "latest"}
    make_links(
        links={**default_links, **ctx.config.links},
        destination=paths.versions,
    )

    await install_wrapper(ctx, paths)


def _build_env_for_package(
    ctx: Context, env_path: Path, main_package: Package, *, staging: bool
) -> None:
    for pkg in chain([main_package], main_package.depends):
        out = ctx.out_any(pkg) if staging else ctx.out_destination(pkg)
        for srcdir, _, files in os.walk(out):
            srcdir_path = Path(srcdir)
            dstdir = env_path / srcdir_path.relative_to(out)
            dstdir.mkdir(parents=True, exist_ok=True)
            for f in files:
                with suppress(FileExistsError):
                    target = os.path.relpath(srcdir_path / f, dstdir)
                    (dstdir / f).symlink_to(target)

    # Write a manifest file
    (env_path / "manifest").write_text(main_package.manifest)


def _get_versions_path(paths: Paths, finalpkg: Package) -> Path | None:
    for i in range(1, 1000):
        path = paths.versions / f"{finalpkg.config.version}+{i}"
        if not path.is_dir():
            return path

        try:
            manifest = (path / "manifest").read_text()
        except FileNotFoundError:
            manifest = ""

        if finalpkg.manifest == manifest:
            print(f"Environment already exists at {path}", file=sys.stderr)
            return None

    sys.exit(
        f"Out of range while trying to find a build number for {finalpkg.config.version}"
    )


async def build_all(ctx: Context, stop_after: Package | None = None) -> None:
    await _build_packages(ctx, stop_after)
    if stop_after is not None:
        return

    await _build_envs(ctx, ctx.staging_paths, staging=True)


async def install_all(ctx: Context, *, target_paths: Paths) -> None:
    for pkg in ctx.packages.values():
        to_path = ctx.out_destination(pkg)

        if to_path.exists():
            print(f"Already installed: {pkg.fullname}", file=sys.stderr)
            continue

        from_path = ctx.out_staging(pkg)
        if not from_path.exists():
            sys.exit(
                f"Package {pkg.fullname} has not been built. Run 'karsk build' first."
            )
        to_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(from_path, to_path)
        print(f"Installed {pkg.fullname} to {to_path}")

    await _build_envs(ctx, target_paths, staging=False)
