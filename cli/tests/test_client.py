"""SyncClient behavior not already covered indirectly via the import/export
integration tests — specifically, what happens when the local API this tool
depends on (see ADR-0009: a running server is a documented precondition,
not something this tool starts itself) isn't actually reachable.
"""

import httpx
import pytest

from promptful_sync.client import SyncClient, SyncClientConnectionError


async def test_raises_a_clear_error_when_the_server_is_unreachable() -> None:
    async with httpx.AsyncClient(base_url="http://localhost:1") as http:
        client = SyncClient(http)

        with pytest.raises(SyncClientConnectionError):
            await client.list_categories()
