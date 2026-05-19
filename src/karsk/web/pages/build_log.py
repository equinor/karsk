from __future__ import annotations
from karsk.web.components import layout
from karsk.web.scanner import StoreEntry, get_store
from fastapi import Depends, APIRouter, Path as FastAPIPath
from karsk.web.web_config import WebConfig, get_web_config
from typing import Annotated
from pydantic import BaseModel, ConfigDict

import htpy as h
from htpy.starlette import HtpyResponse


router = APIRouter(default_response_class=HtpyResponse)


class BuildLogPage(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    web_config: Annotated[WebConfig, Depends(get_web_config)]
    store: Annotated[list[StoreEntry], Depends(get_store)]
    destination_name: Annotated[str, FastAPIPath()]
    name: Annotated[str, FastAPIPath()]

    def __call__(self) -> h.Element:
        for entry in self.store:
            if entry.path.name != self.name:
                continue

            path = entry.path / "build.log"

            return layout(
                page_title=f"Karsk - build log for {self.name}",
                content=[
                    h.a(href=f"/destinations/{self.destination_name}")[
                        f"← Back to {self.destination_name}"
                    ],
                    h.div(".card")[
                        h.div(".card-body")[h.pre(".overflow-scroll")[path.read_text()]]
                    ],
                ],
            )
        else:
            raise KeyError("File not found")


@router.get("/destinations/{destination_name}/store/{name}")
async def get_build_log(view: Annotated[BuildLogPage, Depends()]) -> HtpyResponse:
    return HtpyResponse(view())
