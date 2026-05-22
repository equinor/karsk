from __future__ import annotations
from itertools import chain
import hashlib
from pathlib import Path
import sys
from typing import IO, Any, Self

from asyncio.subprocess import Process
from karsk.config import Config, load_config
from karsk.engine import (
    CpuArchName,
    CpuArchNameNative,
    Engine,
    EngineNameNative,
    VolumeBind,
    get_engine,
)
from karsk.package import Package
from karsk.console import console
from karsk.paths import Paths
import networkx as nx


TARGET_TRIPLETS: dict[CpuArchName, str] = {
    "amd64": "x86_64-unknown-linux",
    "arm64": "aarch64-unknown-linux",
}


class Context:
    def __init__(
        self,
        config: Config,
        *,
        staging: Path,
        engine: EngineNameNative | None = None,
        arch: CpuArchNameNative = "native",
    ) -> None:
        self.config: Config = config
        self.engine: Engine = get_engine(engine, arch)

        cache = staging / "cache"
        if self.engine.name != "native":
            staging = staging / config.main_package / TARGET_TRIPLETS[self.engine.arch]

        self.staging_paths: Paths = Paths(staging, cache=cache, is_staging=True)
        self.destination_paths: Paths = Paths(config.destination)
        self.packages = self._resolve_packages(config)

    @classmethod
    def _initial_hash(cls, config: Config) -> bytes:
        h = hashlib.sha1(usedforsecurity=False)

        h.update(config.destination.as_posix().encode())
        h.update(config.build_image.read_bytes())

        return h.digest()

    @classmethod
    def _resolve_packages(cls, config: Config) -> dict[str, Package]:
        buildmap = {x.name: x for x in config.packages}

        graph: nx.DiGraph[str] = nx.DiGraph()
        for package in config.packages:
            graph.add_node(package.name)
            for dep in package.depends:
                graph.add_edge(dep, package.name)

        initial_hash = cls._initial_hash(config)
        transitive_depends: dict[Package, list[Package]] = {}
        packages: dict[str, Package] = {}
        for node in nx.topological_sort(graph):
            package_config = buildmap[node]

            direct_depends = [packages[x] for x in package_config.depends]
            node_depends = [
                *direct_depends,
                *chain.from_iterable(transitive_depends[x] for x in direct_depends),
            ]

            new_package = Package(
                package_config,
                node_depends,
                config.build_image,
                initial_hash,
            )
            transitive_depends[new_package] = node_depends
            packages[node] = new_package

        return packages

    @property
    def destination(self) -> Path:
        return self.config.destination

    @property
    def can_debug(self) -> bool:
        """Returns True is it's possible to enter an interactive shell for debugging purposes"""
        return sys.stdin.isatty()

    def _out_rw(self, package: Package | str, paths: Paths) -> Path:
        if isinstance(package, str):
            package = self.packages[package]
        return paths.store / package.out_relpath

    def out_staging(self, package: Package | str) -> Path:
        """Helper for obtaining the output path for a given package"""
        return self._out_rw(package, self.staging_paths)

    def out_destination(self, package: Package | str) -> Path:
        """Helper for obtaining the output path for a given package"""
        return self._out_rw(package, self.destination_paths)

    def out_any(self, package: Package | str) -> Path:
        """Look for package anywhere. Return None if it doesn't exist anywhere"""
        if isinstance(package, str):
            package = self.packages[package]
        for store in (self.staging_paths.store, self.destination_paths.store):
            if (path := store / package.out_relpath).is_dir():
                return path

        raise FileNotFoundError()

    def exists(self, package: Package | str) -> bool:
        try:
            self.out_any(package)
            return True
        except FileNotFoundError:
            return False

    def __getitem__(self, key: str) -> Package:
        return self.packages[key]

    @classmethod
    def from_config_file(
        cls,
        config: Path,
        *,
        staging: Path,
        engine: EngineNameNative | None = None,
        arch: CpuArchNameNative = "native",
    ) -> Self:
        config_ = load_config(config)
        return cls(config_, staging=staging, engine=engine, arch=arch)

    @classmethod
    def from_config(
        cls,
        data: dict[str, Any],
        *,
        cwd: Path,
        staging: Path,
        engine: EngineNameNative | None = None,
        arch: CpuArchNameNative = "native",
    ) -> Self:
        config_ = Config.model_validate(data, context={"cwd": cwd})
        return cls(config_, staging=staging, engine=engine, arch=arch)

    def ensure_built(self, packages: list[str] | None = None) -> None:
        """Ensure that packages are present in staging. If 'packages' arg is
        specified, only those packages will be checked. Otherwise every
        package is expected to exist."""

        if packages is None:
            packages = sorted(self.packages.keys())

        missing: list[str] = []
        for pname in packages:
            if (pkg := self.packages.get(pname)) is None:
                raise ValueError(f"No package {pname} defined")

            if not self.out_any(pkg).is_dir():
                missing.append(pname)

        if missing:
            console.log(
                f"[yellow]The following packages haven't been built:[bold] {', '.join(missing)}"
            )
            console.log(
                "[yellow]Run '[bold]karsk build [CONFIG PATH][/bold]' to build all packages"
            )
            sys.exit(1)

    async def run(
        self,
        program: str | Path,
        *args: str | Path,
        package: str | list[str] | None = None,
        volumes: list[VolumeBind] | None = None,
        build: bool = False,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
        terminal: bool = False,
        network: bool = True,
        stdout: IO[Any] | int | None = None,
        stderr: IO[Any] | int | None = None,
    ) -> Process:
        image: Path

        if cwd is None:
            cwd = "/"
        if env is None:
            env = {}
        if volumes is None:
            volumes = []

        if build:
            if not isinstance(package, str):
                raise TypeError(
                    "When build=True, package must be a specific package name (str)"
                )
            image = self.config.build_image
            package = [package]

        else:
            image = self.config.build_image

            if package is None:
                package = sorted(self.packages.keys())
            elif isinstance(package, str):
                package = [package]

            self.ensure_built(package)

        if self.staging_paths.bin.is_dir():
            volumes.append((self.staging_paths.bin, self.destination_paths.bin, "ro"))
        if self.staging_paths.versions.is_dir():
            volumes.append(
                (self.staging_paths.versions, self.destination_paths.versions, "ro")
            )

        return await self.engine(
            image,
            program,
            *args,
            volumes=volumes + self.volumes(package),
            cwd=cwd,
            env=env,
            terminal=terminal,
            network=network,
            stdout=stdout,
            stderr=stderr,
        )

    def volumes(self, package_names: list[str]) -> list[VolumeBind]:
        pnames = set(package_names)
        for pname in package_names:
            pnames |= set(p.config.name for p in self[pname].depends)

        return [(self.out_any(pkg), self.out_destination(pkg), "ro") for pkg in pnames]
