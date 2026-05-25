"""MemoryDB unit tests — especially cross-actor isolation."""

import pytest

from .conftest import DEFAULT_ACTOR_ID, OTHER_ACTOR_ID

ALICE = DEFAULT_ACTOR_ID
BOB = OTHER_ACTOR_ID


@pytest.mark.asyncio
async def test_upsert_and_get(db):
    row = await db.upsert(ALICE, "favorite_color", "blue")
    assert row["key"] == "favorite_color"
    assert row["text"] == "blue"
    assert row["actor_id"] == ALICE
    assert await db.get_by_key(ALICE, "favorite_color") == row


@pytest.mark.asyncio
async def test_upsert_overwrites_existing_key(db):
    a = await db.upsert(ALICE, "k", "v1")
    b = await db.upsert(ALICE, "k", "v2")
    assert a["id"] == b["id"]
    assert b["text"] == "v2"
    assert len(await db.list_for_actor(ALICE)) == 1


@pytest.mark.asyncio
async def test_cross_actor_isolation(db):
    """The security boundary — never relax these assertions."""
    await db.upsert(ALICE, "secret", "alice_secret")
    await db.upsert(BOB, "secret", "bob_secret")

    [a_row] = await db.list_for_actor(ALICE)
    [b_row] = await db.list_for_actor(BOB)
    assert a_row["text"] == "alice_secret"
    assert b_row["text"] == "bob_secret"

    # Each get/update/delete must miss when the actor doesn't own the row.
    assert await db.get_by_id(ALICE, b_row["id"]) is None
    assert await db.update_by_id(ALICE, b_row["id"], text="hacked") is None
    assert await db.delete_by_id(ALICE, b_row["id"]) is False

    # Bob's row is unchanged.
    still = await db.get_by_id(BOB, b_row["id"])
    assert still and still["text"] == "bob_secret"


@pytest.mark.asyncio
async def test_search_scoped_to_actor(db):
    await db.upsert(ALICE, "color", "I like blue skies")
    await db.upsert(ALICE, "food", "tacos and burritos")
    await db.upsert(ALICE, "extras", "the colour blue is calming")
    await db.upsert(BOB, "color", "purple should not appear")

    assert {h["key"] for h in await db.search(ALICE, "blue")} == {"color", "extras"}
    assert {h["key"] for h in await db.search(ALICE, "food")} == {"food"}
    # Bob's row must not leak into alice's results.
    assert await db.search(ALICE, "purple") == []


@pytest.mark.asyncio
async def test_delete_by_key(db):
    await db.upsert(ALICE, "to_delete", "x")
    assert await db.delete_by_key(ALICE, "to_delete") is True
    assert await db.get_by_key(ALICE, "to_delete") is None
    # Second delete is a no-op.
    assert await db.delete_by_key(ALICE, "to_delete") is False


@pytest.mark.asyncio
async def test_update_by_id(db):
    row = await db.upsert(ALICE, "k", "v1")
    updated = await db.update_by_id(ALICE, row["id"], text="v2")
    assert updated and updated["text"] == "v2"
    renamed = await db.update_by_id(ALICE, row["id"], key="renamed")
    assert renamed and renamed["key"] == "renamed"
