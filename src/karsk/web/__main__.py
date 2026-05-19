from __future__ import annotations
import uvicorn


if __name__ == "__main__":
    uvicorn.run("karsk.web.app:app", reload=True)
