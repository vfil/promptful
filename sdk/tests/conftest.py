"""Integration tests drive the real FastAPI app + Postgres over a live HTTP
server (grilled decision: not respx-mocked HTTP, not an in-process ASGI
transport — promptful.Client is sync-only, and httpx's ASGITransport only
supports async clients, so a real bound socket is the only way to exercise it
end-to-end).

Requires the same `app_test` Postgres database the api/ test suite uses
(see api/tests/conftest.py): `docker compose up -d` from api/, with
migrations applied via `POSTGRES_DB=app_test uv run alembic upgrade head`.
"""

import socket
import sys
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

API_ROOT = Path(__file__).resolve().parents[2] / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core.config import Settings  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

test_settings = Settings(postgres_db="app_test")

# NullPool: the live server runs its own event loop in a background thread;
# an asyncpg connection pooled across that boundary can outlive the loop that
# opened it. Mirrors api/tests/conftest.py.
_async_engine = create_async_engine(test_settings.database_url, poolclass=NullPool)
_async_session_factory = async_sessionmaker(bind=_async_engine, expire_on_commit=False)

# Table resets go through the sync driver instead — the SDK's own tests are
# plain sync functions, and this is the only place they touch the database.
_sync_engine = create_engine(test_settings.database_url_sync)


async def _override_get_db():
    async with _async_session_factory() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


class _BackgroundServer(uvicorn.Server):
    def install_signal_handlers(self) -> None:
        pass  # Only valid on the main thread; this server runs on a worker thread.


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def live_base_url():
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = _BackgroundServer(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@pytest.fixture(autouse=True)
def _reset_tables():
    yield
    with _sync_engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE prompts, categories RESTART IDENTITY CASCADE"))
