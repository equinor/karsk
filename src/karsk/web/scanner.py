from __future__ import annotations
from karsk.web.web_config import get_web_config, WebConfig
from fastapi import Depends
from typing import Self, Annotated
from collections import defaultdict

from dataclasses import dataclass, field
from pathlib import Path

from semver import Version

from karsk.paths import Paths


@dataclass
class VersionEntry:
    path: Path
    name: str
    version: Version
    manifest: list[str]
    aliases: list[str] = field(default_factory=list)

    @classmethod
    def scan(cls, path: Path) -> Self:
        return cls(
            path,
            path.name,
            Version.parse(path.name),
            (path / "manifest").read_text().splitlines(),
        )


@dataclass
class StoreEntry:
    path: Path
    name: str
    hash: str
    version: Version
    used_by: set[str] = field(default_factory=set)

    @classmethod
    def scan(cls, path: Path) -> Self:
        hash, name, version = path.name.split("-", maxsplit=2)

        return cls(
            path,
            name,
            hash,
            Version.parse(version),
        )


def scan_versions(paths: Paths) -> list[VersionEntry]:
    entries: list[VersionEntry] = []
    aliases: dict[str, list[str]] = defaultdict(list)

    for path in paths.versions.glob("*/manifest"):
        path = path.parent
        print(path)

        if path.is_symlink():
            aliases[path.resolve().name].append(path.name)
        else:
            entries.append(VersionEntry.scan(path))

    for entry in entries:
        entry.aliases = aliases[entry.name]

    return sorted(entries, key=lambda e: e.version, reverse=True)


def scan_store(paths: Paths) -> list[StoreEntry]:
    entries: list[StoreEntry] = []
    for path in paths.store.iterdir():
        entries.append(StoreEntry.scan(path))

    return entries


def get_destination_paths(
    web_config: Annotated[WebConfig, Depends(get_web_config)],
    destination_name: str,
) -> Paths:
    return Paths(web_config[destination_name])


def get_versions(
    paths: Annotated[Paths, Depends(get_destination_paths)],
) -> list[VersionEntry]:
    return scan_versions(paths)


def get_store(
    paths: Annotated[Paths, Depends(get_destination_paths)],
) -> list[StoreEntry]:
    return scan_store(paths)
