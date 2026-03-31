"""Observability setup — structlog, OpenTelemetry, Sentry.

Wires structured logging, distributed tracing, and error tracking
into the FastAPI application lifecycle.
"""

import structlog

from helix.config import Settings


def setup_logging(settings: Settings) -> None:
    """Configure structlog with JSON output for production, console for dev."""
    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.environment == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    import logging

    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def setup_sentry(settings: Settings) -> None:
    """Initialize Sentry error tracking if DSN is configured."""
    if not settings.sentry_dsn:
        return

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=0.1 if settings.environment == "production" else 1.0,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ],
    )


def setup_opentelemetry(settings: Settings) -> None:
    """Initialize OpenTelemetry tracing if OTLP endpoint is configured."""
    if not settings.otel_exporter_otlp_endpoint:
        return

    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider

    resource = Resource.create({"service.name": "helix-api", "deployment.environment": settings.environment})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)


def init_observability(settings: Settings) -> None:
    """Initialize all observability systems."""
    setup_logging(settings)
    setup_sentry(settings)
    setup_opentelemetry(settings)
