import pytest

from .conftest import setup_datasette


async def _names(ds, kind: str, name: str) -> list[str]:
    result = await ds.get_internal_database().execute(
        "select name from sqlite_master where type = :kind and name = :name",
        {"kind": kind, "name": name},
    )
    return [r["name"] for r in result.rows]


@pytest.mark.asyncio
async def test_table_and_index_exist():
    ds, _ = await setup_datasette()
    assert await _names(ds, "table", "_datasette_agent_actor_memory_note") == [
        "_datasette_agent_actor_memory_note"
    ]
    assert await _names(ds, "index", "idx_aam_note_actor") == ["idx_aam_note_actor"]


@pytest.mark.asyncio
async def test_migrations_idempotent():
    """Running startup a second time must not error or re-apply."""
    ds, _ = await setup_datasette()
    await ds.invoke_startup()
