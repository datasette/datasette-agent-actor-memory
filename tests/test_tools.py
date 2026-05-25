import json

import pytest

from datasette_agent_actor_memory.tools import TOOLS

from .conftest import DEFAULT_ACTOR_ID, OTHER_ACTOR_ID

ALICE = {"id": DEFAULT_ACTOR_ID}
BOB = {"id": OTHER_ACTOR_ID}


def _by_name(name: str):
    for t in TOOLS:
        if t.name == name:
            return t
    raise AssertionError(f"tool {name!r} not registered")


async def _call(name, ds, actor, **params):
    out = await _by_name(name).fn(datasette=ds, actor=actor, **params)
    return json.loads(out)


def test_expected_tools_registered():
    names = {t.name for t in TOOLS}
    assert names == {
        "save_memory",
        "list_memories",
        "search_memories",
        "delete_memory",
    }
    for t in TOOLS:
        assert t.input_schema.get("type") == "object"
        assert t.required_permission is None


@pytest.mark.asyncio
async def test_save_and_list_via_tool(ds_tools):
    saved = await _call(
        "save_memory", ds_tools, ALICE, key="favorite_color", text="blue"
    )
    assert saved["ok"] is True
    assert saved["memory"]["text"] == "blue"
    # _html mounts the matching custom element with a module script
    # pointing at the tool-widget bundle.
    assert "<aam-memory-saved>" in saved["_html"]
    assert 'type="module"' in saved["_html"]
    assert "tool-widget" in saved["_html"]

    listed = await _call("list_memories", ds_tools, ALICE)
    assert [m["key"] for m in listed["memories"]] == ["favorite_color"]
    assert "<aam-memory-list>" in listed["_html"]


@pytest.mark.asyncio
async def test_search_and_delete_via_tool(ds_tools):
    await _call("save_memory", ds_tools, ALICE, key="color", text="sky is blue")
    await _call("save_memory", ds_tools, ALICE, key="food", text="tacos rule")

    sresult = await _call("search_memories", ds_tools, ALICE, query="blue")
    assert {h["key"] for h in sresult["memories"]} == {"color"}
    assert sresult["query"] == "blue"
    assert "<aam-memory-search>" in sresult["_html"]

    deleted = await _call("delete_memory", ds_tools, ALICE, key="color")
    assert deleted["ok"] is True
    assert "<aam-memory-deleted>" in deleted["_html"]

    again = await _call("delete_memory", ds_tools, ALICE, key="color")
    assert again["ok"] is False


@pytest.mark.asyncio
async def test_tools_isolate_actors(ds_tools):
    await _call("save_memory", ds_tools, ALICE, key="secret", text="alice")
    await _call("save_memory", ds_tools, BOB, key="secret", text="bob")

    alice_rows = (await _call("list_memories", ds_tools, ALICE))["memories"]
    bob_rows = (await _call("list_memories", ds_tools, BOB))["memories"]
    assert [r["text"] for r in alice_rows] == ["alice"]
    assert [r["text"] for r in bob_rows] == ["bob"]


@pytest.mark.asyncio
@pytest.mark.parametrize("actor", [None, {}])
async def test_tools_reject_missing_actor(ds_tools, actor):
    with pytest.raises(PermissionError):
        await _call("save_memory", ds_tools, actor, key="k", text="t")
