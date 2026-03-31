"""Helix — Enterprise AI Agent Orchestration Platform."""

from fastapi import FastAPI

from helix.api.routes import agents, approvals, audit, integrations, memory, orgs, workflows, ws
from helix.config import get_settings
from helix.observability import init_observability


def create_app() -> FastAPI:
    """Application factory for the Helix API."""
    settings = get_settings()
    init_observability(settings)

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
    app.include_router(agents.router, prefix="/api/v1")
    app.include_router(integrations.router, prefix="/api/v1")
    app.include_router(audit.router, prefix="/api/v1")
    app.include_router(ws.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
