from __future__ import annotations
from htpy.starlette import HtpyResponse

from fastapi import FastAPI

from karsk.web.pages.index import router as index_router
from karsk.web.pages.overview import router as overview_router
from karsk.web.pages.build_log import router as build_log_router


app = FastAPI(title="Karsk Web", default_response_class=HtpyResponse)

app.include_router(index_router)
app.include_router(overview_router)
app.include_router(build_log_router)
