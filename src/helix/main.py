"""Helix — Enterprise AI Agent Orchestration Platform."""

from fastapi import FastAPI

from helix.api.routes import approvals, memory, orgs, workflows
from helix.config import get_settings


def create_app() -> FastAPI:
    """Application factory for the Helix API."""
    settings = get_settings()

    app = FastAPI(
        title="Helix",
        description="Enterprise AI Agent Orchestration Platform",
        version="0.1.0",
        debug=settings.debug,
    )

    # Routes
    app.include_router(orgs.router, prefix="/api/v1")
    app.include_router(workflows.router, prefix="/api/v1")
    app.include_router(memory.router, prefix="/api/v1")
    app.include_router(approvals.router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
