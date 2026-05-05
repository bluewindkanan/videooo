from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.src.server.routes.video_tasks import router as video_tasks_router
from app.src.artifacts.store import ArtifactStore
from app.src.storage.sqlite import SqliteStore


from typing import Optional


def create_app(*, db_path: Optional[str] = None) -> FastAPI:
    app = FastAPI(title="videooo")
    app.include_router(video_tasks_router)

    resolved_db_path = db_path or os.environ.get("VIDEOOO_DB_PATH") or "app/.local/videooo.sqlite3"
    app.state.store = SqliteStore(resolved_db_path)
    artifact_base_dir = os.environ.get("VIDEOOO_ARTIFACT_DIR") or "app/.artifacts"
    app.state.artifact_store = ArtifactStore(artifact_base_dir)
    web_dir = Path(__file__).resolve().parents[1] / "web"

    @app.get("/workbench")
    def workbench() -> FileResponse:
        return FileResponse(str(web_dir / "workbench.html"))

    @app.get("/workbench.js")
    def workbench_js() -> FileResponse:
        return FileResponse(str(web_dir / "workbench.js"))

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
