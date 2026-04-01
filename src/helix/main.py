"""Helix — Enterprise AI Agent Orchestration Platform."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from helix.api.routes import (
    agents,
    approvals,
    audit,
    generate,
    integrations,
    memory,
    orgs,
    usage,
    workflows,
    ws,
)
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

    # CORS — must be added BEFORE any other middleware so that preflight
    # OPTIONS requests receive proper headers even when auth rejects (401).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    # Routes
    app.include_router(orgs.router, prefix="/api/v1")
    app.include_router(workflows.router, prefix="/api/v1")
    app.include_router(memory.router, prefix="/api/v1")
    app.include_router(approvals.router, prefix="/api/v1")
    app.include_router(agents.router, prefix="/api/v1")
    app.include_router(integrations.router, prefix="/api/v1")
    app.include_router(audit.router, prefix="/api/v1")
    app.include_router(usage.router, prefix="/api/v1")
    app.include_router(generate.router, prefix="/api/v1")
    app.include_router(ws.router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
