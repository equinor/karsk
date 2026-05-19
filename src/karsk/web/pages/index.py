from __future__ import annotations
from karsk.web.components import layout
from typing import Annotated
from pydantic import BaseModel
from karsk.web.web_config import WebConfig, get_web_config
from fastapi import APIRouter, Depends
import htpy as h
from htpy.starlette import HtpyResponse


router = APIRouter(default_response_class=HtpyResponse)


class IndexPage(BaseModel):
    web_config: Annotated[WebConfig, Depends(get_web_config)]

    def __call__(self) -> h.Element:
        if len(self.web_config.root) == 0:
            return layout(content=h.p(".text-muted")["No destinations configured"])

        return layout(
            content=h.div(".container.py-4")[
                h.ul(".list-group")[
                    [
                        h.li(".list-group-item")[
                            h.a(
                                ".text-decoration-none",
                                href=f"/destinations/{name}",
                            )[
                                h.div(".fw-bold")[name],
                                h.small(".text-muted")[str(path)],
                            ]
                        ]
                        for name, path in self.web_config.root.items()
                    ]
                ]
            ],
        )


@router.get("/")
async def index(view: Annotated[IndexPage, Depends()]) -> HtpyResponse:
    return HtpyResponse(view())
