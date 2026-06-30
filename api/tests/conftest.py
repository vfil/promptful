import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.db.session import get_db
from app.main import app

# Q1 (grilling session): integration tests run against the same docker-compose
# Postgres used for local dev, pointed at a dedicated `app_test` database that
# already has migrations applied (`POSTGRES_DB=app_test uv run alembic upgrade head`).
#
# NullPool: pytest-asyncio opens a fresh event loop per test function: an
# asyncpg connection pooled across that boundary fails ("another operation is
# in progress") because the connection is still bound to a now-closed loop.
# NullPool opens (and closes) a real connection per checkout instead of
# reusing one across tests/loops.
test_settings = Settings(postgres_db="app_test")
test_engine = create_async_engine(test_settings.database_url, poolclass=NullPool)
test_session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def _reset_prompts_table():
    yield
    async with test_engine.begin() as connection:
        await connection.execute(text("TRUNCATE TABLE prompts"))


@pytest_asyncio.fixture
async def client():
    """httpx client driving the real FastAPI app in-process, with get_db swapped
    for sessions bound to the `app_test` database. Each request gets its own
    session from the pool, exactly as in production; `_reset_prompts_table`
    above clears state between tests."""

    async def override_get_db():
        async with test_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
