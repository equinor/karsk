from __future__ import annotations
from pathlib import Path

from karsk.package import Package


class Paths:
    def __init__(
        self,
        base: Path,
        *,
        cache: Path | None = None,
        is_staging: bool = False,
    ) -> None:
        base = base.absolute()
        self._base = base
        self._cache = cache
        self._is_staging = is_staging

        self.bin = base / "bin"
        self.versions = base / "versions"
        self.store = base / "store"

        if is_staging:
            self.store.mkdir(parents=True, exist_ok=True)

    @property
    def cache(self) -> Path:
        self._assert_not_staging("Cache path")
        assert self._cache is not None
        return self._cache

    @property
    def builds(self) -> Path:
        self._assert_not_staging("Builds path")
        return self._base / "builds"

    def src(self, pkg: Package) -> Path | None:
        if (p := pkg.src_relpath) is None:
            return None
        return self.cache / p

    def _assert_not_staging(self, name: str) -> None:
        if not self._is_staging:
            raise RuntimeError(f"{name} only exists in staging")
