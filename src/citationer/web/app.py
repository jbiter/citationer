"""FastAPI 应用工厂。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from citationer import __version__
from citationer.web.routers import charts, compare, data, network, stats


def create_app() -> FastAPI:
    app = FastAPI(
        title="Citationer",
        description="本地文献题录分析仪表板",
        version=__version__,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
    app.include_router(network.router, prefix="/api/network", tags=["network"])
    app.include_router(compare.router, prefix="/api/compare", tags=["compare"])
    app.include_router(data.router, prefix="/api/data", tags=["data"])
    app.include_router(charts.router, prefix="/api/charts", tags=["charts"])

    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app
