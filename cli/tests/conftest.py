"""Integration tests drive the real FastAPI app (from ../api) in-process over
ASGITransport, against the same `app_test` Postgres database api/tests and
sdk/tests use.

Unlike sdk/tests/conftest.py (which boots a real uvicorn server on a real
port, because promptful.Client is sync-only and ASGITransport only supports
async clients), this package's SyncClient is already async — so the lighter
in-process ASGITransport approach api/tests/conftest.py itself uses works
directly here too, no real socket needed. The `sys.path` reach into ../api is
the same trick sdk/tests/conftest.py uses to get at the real app.

Requires: `docker compose up -d` from api/, with migrations applied via
`POSTGRES_DB=app_test uv run alembic upgrade head`.
"""

import sys
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

API_ROOT = Path(__file__).resolve().parents[2] / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core.config import Settings  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

from promptful_sync.client import SyncClient  # noqa: E402

test_settings = Settings(postgres_db="app_test")
test_engine = create_async_engine(test_settings.database_url, poolclass=NullPool)
test_session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def _reset_tables():
    yield
    async with test_engine.begin() as connection:
        await connection.execute(text("TRUNCATE TABLE prompts, categories RESTART IDENTITY CASCADE"))


@pytest_asyncio.fixture
async def client():
    """Raw httpx.AsyncClient bound to the real app in-process — exposed
    directly (not just via `sync_client`) for tests that need to reach the
    API in ways SyncClient deliberately doesn't expose, e.g. DELETE."""

    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sync_client(client: AsyncClient) -> SyncClient:
    return SyncClient(client)
