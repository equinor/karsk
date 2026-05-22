from textwrap import dedent
from karsk.paths import Paths
import os
from pathlib import Path

import pytest

from karsk.builder import build_all, install_all
from karsk.context import Context


@pytest.fixture(autouse=True)
def stub_build_wrapper(mocker):
    mocker.patch("karsk.wrapper.build_wrapper", return_value=Path("/usr/bin/true"))


@pytest.fixture
def base_config(tmp_path):
    return {
        "destination": str(tmp_path / "destination"),
        "main-package": "test",
        "entrypoints": ["test_script.sh"],
        "build-image": os.path.join(os.path.dirname(__file__), "test_build_image"),
        "packages": [],
    }


async def test_install_copies_to_destination(tmp_path, base_config):
    (tmp_path / "script.sh").write_text(
        dedent("""\
        #!/usr/bin/env bash
        echo hello
        """)
    )
    base_config["packages"].append(
        {
            "name": "test",
            "version": "1.0.0",
            "src": {"type": "file", "path": str(tmp_path / "script.sh")},
            "build": dedent("""\
                mkdir -p $out/bin
                cp $src $out/bin/test_script.sh
                chmod +x $out/bin/test_script.sh
            """),
        }
    )

    ctx = Context.from_config(
        base_config,
        cwd=tmp_path,
        staging=tmp_path / "staging",
        engine="fake",
    )
    await build_all(ctx)

    assert not ctx.destination.exists()

    await install_all(ctx, target_paths=ctx.destination_paths)

    assert ctx.destination.exists()
    assert (ctx.destination / "store").is_dir()
    assert (ctx.destination / "bin/test_script.sh").exists()
    assert (ctx.destination / "versions/latest").is_symlink()
    assert (ctx.destination / "versions/stable").is_symlink()


async def test_install_idempotent(tmp_path: Path, base_config):
    build_dir = tmp_path / "build"
    destination = tmp_path / "destination"
    base_config["destination"] = str(build_dir)

    base_config["packages"].append(
        {
            "name": "test",
            "version": "1.0.0",
            "build": "mkdir -p $out/bin\n",
        }
    )

    ctx = Context.from_config(
        base_config, cwd=tmp_path, staging=build_dir, engine="native"
    )
    await build_all(ctx, stop_after=ctx["test"])

    await install_all(ctx, target_paths=Paths(destination))
    assert (destination / "versions/1.0.0+1").is_dir()

    await install_all(ctx, target_paths=Paths(destination))
    assert (destination / "versions/1.0.0+1").is_dir()
    assert not (destination / "versions/1.0.0+2").exists()
