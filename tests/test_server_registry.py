from unittest.mock import AsyncMock

import pytest

from server_registry import ServerRegistry


def make_client(*return_batches):
    """A fake CraftyClient whose list_servers yields each batch in turn."""
    client = AsyncMock()
    client.list_servers = AsyncMock(side_effect=list(return_batches))
    return client


@pytest.mark.asyncio
async def test_first_refresh_populates_and_reports_all_as_added():
    client = make_client(
        [{"id": "a", "name": "Alpha"}, {"id": "b", "name": "Beta"}],
    )
    registry = ServerRegistry(client)

    diff = await registry.refresh()

    assert set(registry.servers) == {"a", "b"}
    assert registry.servers["a"] == {"id": "a", "name": "Alpha"}
    assert {e["id"] for e in diff.added} == {"a", "b"}
    assert diff.removed == []
    assert diff.has_changes is True
    assert registry.last_refresh_ok is True


@pytest.mark.asyncio
async def test_second_refresh_reports_only_the_delta():
    client = make_client(
        [{"id": "a", "name": "Alpha"}, {"id": "b", "name": "Beta"}],
        [{"id": "a", "name": "Alpha"}, {"id": "c", "name": "Gamma"}],
    )
    registry = ServerRegistry(client)

    await registry.refresh()
    diff = await registry.refresh()

    assert set(registry.servers) == {"a", "c"}
    assert [e["id"] for e in diff.added] == ["c"]
    assert [e["id"] for e in diff.removed] == ["b"]


@pytest.mark.asyncio
async def test_no_change_returns_empty_diff():
    client = make_client(
        [{"id": "a", "name": "Alpha"}],
        [{"id": "a", "name": "Alpha"}],
    )
    registry = ServerRegistry(client)

    await registry.refresh()
    diff = await registry.refresh()

    assert diff.added == []
    assert diff.removed == []
    assert diff.has_changes is False


@pytest.mark.asyncio
async def test_refresh_failure_keeps_last_known_cache():
    client = AsyncMock()
    client.list_servers = AsyncMock(
        side_effect=[
            [{"id": "a", "name": "Alpha"}],
            RuntimeError("crafty down"),
        ]
    )
    registry = ServerRegistry(client)

    await registry.refresh()
    diff = await registry.refresh()

    # Cache preserved, empty diff, failure flagged
    assert set(registry.servers) == {"a"}
    assert diff.has_changes is False
    assert registry.last_refresh_ok is False
    assert registry.last_refresh_error is not None


@pytest.mark.asyncio
async def test_seed_populates_without_emitting_a_diff():
    client = make_client([{"id": "a", "name": "Alpha"}])
    registry = ServerRegistry(client)

    registry.seed({"z": {"id": "z", "name": "Seeded"}})

    assert set(registry.servers) == {"z"}

    # A subsequent successful refresh diffs against the seeded cache
    diff = await registry.refresh()
    assert [e["id"] for e in diff.added] == ["a"]
    assert [e["id"] for e in diff.removed] == ["z"]
