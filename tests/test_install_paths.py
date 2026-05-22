import os
import shutil
from pathlib import Path
from subprocess import check_output

import pytest

from karsk.builder import _build_envs, install_all
from karsk.context import Context


@pytest.fixture(autouse=True)
def stub_build_wrapper(mocker):
    mocker.patch("karsk.wrapper.build_wrapper", return_value=Path("/usr/bin/true"))


@pytest.fixture(
    params=[
        pytest.param(
            ("staging", "destination"),
            id="sibling-paths",
        ),
        pytest.param(
            (
                "home/user/workspace/builds/deploy/deploy/staging",
                "opt/app",
            ),
            id="deep-staging-short-destination",
        ),
        pytest.param(
            (
                "staging",
                "project/shared/karsk/app",
            ),
            id="short-staging-deep-destination",
        ),
    ]
)
def paths(tmp_path, request):
    staging_rel, dest_rel = request.param
    return tmp_path / staging_rel, tmp_path / dest_rel


@pytest.fixture
def installed_ctx(paths):
    """Build and install a single-package config, return (ctx, staging, destination)."""
    staging, destination = paths

    config = {
        "destination": str(destination),
        "main-package": "app",
        "entrypoints": ["app"],
        "build-image": os.path.join(os.path.dirname(__file__), "test_build_image"),
        "packages": [
            {"name": "app", "version": "1.0.0", "build": "mkdir -p $out/bin\n"},
        ],
    }

    ctx = Context.from_config(
        config, cwd=staging.parent, staging=staging, engine="native"
    )

    out = ctx.out_staging("app")
    out.mkdir(parents=True, exist_ok=True)
    (out / "bin").mkdir(parents=True, exist_ok=True)
    (out / "bin/app").write_text("#!/bin/bash\necho hi\n")
    (out / "bin/app").chmod(0o755)
    (out / "lib").mkdir(parents=True, exist_ok=True)
    (out / "lib/libcore.so").write_text("fake")

    return ctx, staging, destination


@pytest.fixture
def installed_dep_ctx(paths):
    """Build and install a config with a dependency, return (ctx, staging, destination)."""
    staging, destination = paths

    config = {
        "destination": str(destination),
        "main-package": "app",
        "entrypoints": ["app"],
        "build-image": os.path.join(os.path.dirname(__file__), "test_build_image"),
        "packages": [
            {"name": "liba", "version": "2.0.0", "build": "mkdir -p $out/lib\n"},
            {
                "name": "app",
                "version": "1.0.0",
                "depends": ["liba"],
                "build": "mkdir -p $out/bin\n",
            },
        ],
    }

    ctx = Context.from_config(
        config, cwd=staging.parent, staging=staging, engine="native"
    )

    for pkg_name, files in [
        ("liba", {"lib/libfoo.so": "fake-lib"}),
        ("app", {"bin/app": "#!/bin/bash\necho hi\n"}),
    ]:
        out = ctx.out_staging(pkg_name)
        out.mkdir(parents=True, exist_ok=True)
        for relpath, content in files.items():
            p = out / relpath
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)

    return ctx, staging, destination


@pytest.fixture
def uname():
    return check_output(["uname", "-mo"], text=True).strip()


def _all_symlinks(base: Path) -> list[tuple[Path, str]]:
    return [(p, os.readlink(p)) for p in sorted(base.rglob("*")) if p.is_symlink()]


async def test_symlinks_resolve_within_destination(installed_ctx):
    ctx, _, destination = installed_ctx
    await _build_envs(ctx, ctx.staging_paths, staging=True)
    await install_all(ctx, target_paths=ctx.destination_paths)

    for link, raw_target in _all_symlinks(destination):
        resolved = link.resolve()
        assert str(resolved).startswith(str(destination)), (
            f"Symlink escapes destination:\n"
            f"  link: {link.relative_to(destination)}\n"
            f"  target: {raw_target}\n"
            f"  resolves to: {resolved}"
        )


async def test_destination_self_contained_after_staging_removal(installed_ctx):
    """All symlinks must resolve after staging is deleted."""
    ctx, staging, destination = installed_ctx
    await _build_envs(ctx, ctx.staging_paths, staging=True)
    await install_all(ctx, target_paths=ctx.destination_paths)

    shutil.rmtree(staging)

    broken = [
        (p.relative_to(destination), os.readlink(p))
        for p in destination.rglob("*")
        if p.is_symlink() and not p.resolve().exists()
    ]
    assert broken == [], "Broken symlinks after staging removal:\n" + "\n".join(
        f"  {link} -> {target}" for link, target in broken
    )


async def test_entrypoints_do_not_embed_staging_path(installed_ctx):
    ctx, staging, destination = installed_ctx
    await _build_envs(ctx, ctx.staging_paths, staging=True)
    await install_all(ctx, target_paths=ctx.destination_paths)

    bin_dir = destination / "bin"

    for entry in bin_dir.iterdir():
        if entry.is_symlink() or not entry.is_file():
            continue
        content = entry.read_bytes()
        assert str(staging).encode() not in content, (
            f"Entrypoint {entry.name} embeds staging path"
        )


@pytest.fixture
def fake_ssh(monkeypatch):
    import karsk.syncer

    monkeypatch.setattr(
        karsk.syncer,
        "_RSH",
        ["/bin/sh", "-c", 'shift; exec "$@"', "fake_ssh"],
    )


async def test_sync_does_not_pass_staging_paths_to_rsync(
    installed_ctx, fake_ssh, uname, mocker
):
    """The rsync invocations must reference destination paths only."""
    import asyncio
    from karsk.config import AreaConfig
    from karsk.syncer import sync_all

    ctx, staging, destination = installed_ctx
    await _build_envs(ctx, ctx.staging_paths, staging=True)
    await install_all(ctx, target_paths=ctx.destination_paths)

    calls: list[tuple] = []
    real_exec = asyncio.create_subprocess_exec

    async def capture_exec(*args, **kwargs):
        calls.append(args)
        return await real_exec(*args, **kwargs)

    mocker.patch("asyncio.create_subprocess_exec", side_effect=capture_exec)

    areas = [AreaConfig(name="local", host="localhost")]
    await sync_all(ctx, areas, uname=uname)

    rsync_calls = [c for c in calls if c[0] == "rsync"]
    staging_str = str(staging)
    for call in rsync_calls:
        call_str = " ".join(str(a) for a in call)
        assert staging_str not in call_str, (
            f"rsync invocation contains staging path:\n  {call_str}"
        )
