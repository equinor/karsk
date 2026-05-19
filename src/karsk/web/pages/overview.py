from __future__ import annotations
from karsk.web.components import layout
from karsk.web.scanner import VersionEntry, StoreEntry, get_versions, get_store
from fastapi import Depends, APIRouter, Path as FastAPIPath
from karsk.web.web_config import WebConfig, get_web_config
from typing import Annotated, Callable, TypeVar
from pydantic import BaseModel, ConfigDict

import htpy as h
from htpy.starlette import HtpyResponse


router = APIRouter(default_response_class=HtpyResponse)


T = TypeVar("T")


class OverviewPage(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    web_config: Annotated[WebConfig, Depends(get_web_config)]
    versions: Annotated[list[VersionEntry], Depends(get_versions)]
    store: Annotated[list[StoreEntry], Depends(get_store)]
    destination_name: Annotated[str, FastAPIPath()]

    def __call__(self) -> h.Element:
        return layout(
            page_title=f"Karsk - {self.destination_name}",
            content=[
                h.a(href="/")["← Back to destinations list"],
                self._section("Versions", self.versions, self._render_version),
                self._section("Store", self.store, self._render_store),
            ],
        )

    def _section(
        self, title: str, objects: list[T], render: Callable[[T], h.Element]
    ) -> h.Element:
        return h.div(".card")[
            h.div(".fs-4.card-header")[title],
            h.ul(".list-group.list-group-flush")[[render(obj) for obj in objects]],
        ]

    def _render_version(self, entry: VersionEntry) -> h.Element:
        return h.li(
            ".list-group-item.d-flex.justify-content-between.align-items-center"
        )[
            entry.name,
            h.div(".d-flex.gap-2")[
                [h.div(".badge.bg-primary")[alias] for alias in entry.aliases]
            ],
        ]

    def _render_store(self, entry: StoreEntry) -> h.Element:
        return h.li(
            ".list-group-item.d-flex.justify-content-between.align-items-center"
        )[
            h.div(".ms-2.me-auto")[
                h.div(".fw-bold")[entry.name],
                h.div(".text-muted")[
                    str(entry.version),
                    h.abbr(".ms-2", title=entry.hash)[entry.hash[:6]],
                ],
            ],
            h.a(href=f"/destinations/{self.destination_name}/store/{entry.path.name}")[
                "build log"
            ],
        ]


@router.get("/destinations/{destination_name}")
async def get_overview(view: Annotated[OverviewPage, Depends()]) -> HtpyResponse:
    return HtpyResponse(view())
