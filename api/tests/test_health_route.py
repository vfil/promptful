from sqlalchemy.exc import OperationalError

from app.db.session import engine, get_db
from app.main import app


async def test_health_returns_ok(client):
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_returns_503_when_db_is_unreachable(client):
    class BrokenSession:
        async def execute(self, *args, **kwargs):
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    async def broken_get_db():
        yield BrokenSession()

    app.dependency_overrides[get_db] = broken_get_db

    response = await client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_engine_pre_pings_connections():
    # Reads a private SQLAlchemy attribute on purpose: it's the only way to
    # guard the production engine's config, since the `client` fixture swaps
    # in a test engine. Drop this test if `_pre_ping` ever goes away.
    assert engine.pool._pre_ping is True
