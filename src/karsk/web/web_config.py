from __future__ import annotations
from pathlib import Path
from anyio.functools import lru_cache
import os
from pydantic import RootModel, DirectoryPath


class WebConfig(RootModel[dict[str, DirectoryPath]]):
    def __getitem__(self, key: str) -> Path:
        return self.root[key]


def load_web_config() -> WebConfig:
    path = os.environ.get("KARSK_WEB_CONFIG", "karsk-web.json")
    with open(path, "rb") as f:
        return WebConfig.model_validate_json(f.read())


@lru_cache()
def get_web_config() -> WebConfig:
    return load_web_config()
