from __future__ import annotations
from pathlib import Path

from karsk.package import Package


class Paths:
    def __init__(self, base: Path, *, is_staging: bool = False) -> None:
        base = base.absolute()
        self._base: Path = base
        self._is_staging: bool = is_staging

        self.bin: Path = base / "bin"
        self.versions: Path = base / "versions"
        self.store: Path = base / "store"

    @property
    def cache(self) -> Path:
        self._assert_not_staging("Cache path")
        return self._base / "cache"

    @property
    def builds(self) -> Path:
        self._assert_not_staging("Builds path")
        return self._base / "builds"

    def out(self, pkg: Package) -> Path:
        return self.store / pkg.out_relpath

    def src(self, pkg: Package) -> Path | None:
        if (p := pkg.src_relpath) is None:
            return None
        return self.cache / p

    def _assert_not_staging(self, name: str) -> None:
        if not self._is_staging:
            raise RuntimeError(f"{name} only exists in staging")
