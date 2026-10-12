$ErrorActionPreference = "Stop"

# S0-RUT-1 initial scaffold for AI_based_Symptom_Checker.
# Run from the repository root on rutva0607/S0-RUT-1-fastapi-foundation.
# This script refuses to overwrite existing project files.

$expectedBranch = "rutva0607/S0-RUT-1-fastapi-foundation"
$branch = (git branch --show-current).Trim()

if ($branch -ne $expectedBranch) {
    throw "Safety stop: current branch is '$branch'. Switch to '$expectedBranch' before running this script."
}

if (-not (Test-Path ".git")) {
    throw "Run this script from the AI_based_Symptom_Checker repository root."
}

$files = [ordered]@{
    "server\requirements.txt" = @'
fastapi==0.115.12
uvicorn[standard]==0.34.0
pydantic==2.11.3
pydantic-settings==2.8.1
structlog==25.2.0
SQLAlchemy==2.0.40
alembic==1.15.2
psycopg[binary]==3.2.6
'@
    "server\requirements-dev.txt" = @'
-r requirements.txt
pytest==8.3.5
httpx==0.28.1
ruff==0.11.5
mypy==1.15.0
'@
    "server\pyproject.toml" = @'
[tool.ruff]
line-length = 100
target-version = "py312"
src = ["app", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.ruff.format]
quote-style = "double"

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
mypy_path = "."

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"
'@
    "server\.dockerignore" = @'
.venv
__pycache__
*.py[cod]
.pytest_cache
.mypy_cache
.ruff_cache
tests
.env
.env.*
*.onnx
.git
'@
    "server\Dockerfile" = @'
# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim
ARG GIT_SHA=dev
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION=${GIT_SHA} \
    PORT=8000
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels
COPY --chown=app:app . .
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ[\"PORT\"]}/api/v1/health', timeout=4)"
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
'@
    "server\app\__init__.py" = @'
"""Symptom Checker API application package."""
'@
    "server\app\api\__init__.py" = @'
"""API routers."""
'@
    "server\app\api\v1\__init__.py" = @'
"""Version 1 API endpoints."""
'@
    "server\app\api\v1\health.py" = @'
"""Health-check endpoint."""
from fastapi import APIRouter, Request

from app.core.config import get_settings

router = APIRouter()


@router.get("/health", tags=["health"])
def health(request: Request) -> dict[str, str]:
    """Return service health and the deployed application version."""
    settings = get_settings()
    return {"status": "ok", "version": settings.app_version}
'@
    "server\app\api\v1\router.py" = @'
"""Version 1 API router."""
from fastapi import APIRouter

from app.api.v1.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
'@
    "server\app\core\__init__.py" = @'
"""Core application configuration and utilities."""
'@
    "server\app\core\config.py" = @'
"""Environment-backed application settings."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "AI-Based Symptom Checker API"
    app_version: str = "dev"
    environment: str = "development"
    database_url: str = "postgresql+psycopg://symptom_checker:symptom_checker@localhost:5432/symptom_checker"
    ai_provider: str = "mock"
    cv_provider: str = "mock"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Cache settings for the lifetime of the process."""
    return Settings()
'@
    "server\app\core\logging.py" = @'
"""Structured JSON logging configuration."""
import logging
import sys

import structlog


def configure_logging() -> None:
    """Configure standard-library and structlog loggers for JSON output."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
'@
    "server\app\core\errors.py" = @'
"""Centralized application error handling."""
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = structlog.get_logger(__name__)


class AppError(Exception):
    """Expected application error with a safe public message."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Convert known application errors into a consistent JSON response."""
    logger.warning(
        "application_error",
        code=exc.code,
        status_code=exc.status_code,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unexpected failures without exposing internal details to clients."""
    logger.exception("unhandled_error", path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred.",
                "details": {},
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register centralized exception handlers."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
'@
    "server\app\main.py" = @'
"""FastAPI application factory and ASGI entry point."""
from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    configure_logging()
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Informational symptom assessment API; not a medical diagnosis.",
    )
    application.include_router(api_router, prefix="/api/v1")
    register_error_handlers(application)
    return application


app = create_app()
'@
    "server\tests\test_health.py" = @'
"""Tests for the health endpoint."""
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_status_and_version(monkeypatch) -> None:
    """Health endpoint returns the configured version."""
    monkeypatch.setenv("APP_VERSION", "test-version")
    from app.core.config import get_settings

    get_settings.cache_clear()
    try:
        client = TestClient(create_app())
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": "test-version"}
    finally:
        get_settings.cache_clear()
'@
    ".env.example" = @'
# Local development defaults; never put real secrets in this file.
APP_VERSION=dev
ENVIRONMENT=development
PORT=8000
DATABASE_URL=postgresql+psycopg://symptom_checker:symptom_checker@db:5432/symptom_checker
AI_PROVIDER=mock
CV_PROVIDER=mock
'@
    "docker-compose.yml" = @'
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: symptom_checker
      POSTGRES_USER: symptom_checker
      POSTGRES_PASSWORD: symptom_checker
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U symptom_checker -d symptom_checker"]
      interval: 5s
      timeout: 3s
      retries: 10

  api:
    build:
      context: ./server
      args:
        GIT_SHA: ${APP_VERSION:-dev}
    environment:
      APP_VERSION: ${APP_VERSION:-dev}
      ENVIRONMENT: ${ENVIRONMENT:-development}
      PORT: 8000
      DATABASE_URL: postgresql+psycopg://symptom_checker:symptom_checker@db:5432/symptom_checker
      AI_PROVIDER: ${AI_PROVIDER:-mock}
      CV_PROVIDER: ${CV_PROVIDER:-mock}
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy

volumes:
  postgres_data:
'@
}

$directories = @(
    "server\app\api\v1",
    "server\app\core",
    "server\tests"
)
foreach ($directory in $directories) {
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
}

$existing = @()
foreach ($path in $files.Keys) {
    if (Test-Path $path) { $existing += $path }
}
if ($existing.Count -gt 0) {
    throw "Safety stop: these target files already exist, so nothing was written: $($existing -join ', '). Inspect them first; do not overwrite blindly."
}

foreach ($entry in $files.GetEnumerator()) {
    $parent = Split-Path -Parent $entry.Key
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    Set-Content -LiteralPath $entry.Key -Value $entry.Value -Encoding utf8
    Write-Host "Created $($entry.Key)"
}

Write-Host ""
Write-Host "Initial scaffold created. Next: create/activate venv, install requirements, and run tests."
