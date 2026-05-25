import pytest

from .conftest import (
    DEFAULT_ACTOR_ID,
    OTHER_ACTOR_ID,
    actor_cookie,
    setup_datasette,
)

BASE = "/-/agents-actor-memory/api/memories"
PAGE = "/-/agents-actor-memory/"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,path,body",
    [
        ("GET", BASE, None),
        ("POST", BASE, {"key": "k", "text": "t"}),
        ("GET", f"{BASE}/1", None),
        ("POST", f"{BASE}/1", {"text": "x"}),
        ("POST", f"{BASE}/1/delete", None),
        ("GET", f"{BASE}/search?q=x", None),
    ],
)
async def test_anon_api_is_403(ds_anon, method, path, body):
    ds, _ = ds_anon
    kwargs = {"json": body} if body is not None else {}
    res = await ds.client.request(method, path, **kwargs)
    assert res.status_code == 403
    assert res.json() == {"error": "auth required"}


@pytest.mark.asyncio
async def test_anon_page_redirects_to_login(ds_anon):
    ds, _ = ds_anon
    res = await ds.client.get(PAGE)
    assert res.status_code in (301, 302, 307)
    assert "/-/login" in res.headers.get("location", "")


@pytest.mark.asyncio
async def test_html_page_renders_for_authed_actor(ds_memory):
    ds, _ = ds_memory
    res = await ds.client.get(PAGE)
    assert res.status_code == 200
    assert b"app-root" in res.content
    # actor id is in the embedded page_data
    assert DEFAULT_ACTOR_ID.encode() in res.content


@pytest.mark.asyncio
async def test_create_list_search_update_delete(ds_memory):
    ds, _ = ds_memory

    assert (await ds.client.get(BASE)).json() == {"memories": []}

    # create
    res = await ds.client.post(BASE, json={"key": "color", "text": "blue"})
    assert res.status_code == 200, res.text
    note_id = res.json()["memory"]["id"]

    # list
    body = (await ds.client.get(BASE)).json()
    assert [m["key"] for m in body["memories"]] == ["color"]

    # get by id
    res = await ds.client.get(f"{BASE}/{note_id}")
    assert res.status_code == 200
    assert res.json()["memory"]["text"] == "blue"

    # search hit and miss
    hit = await ds.client.get(f"{BASE}/search?q=blu")
    assert len(hit.json()["memories"]) == 1
    miss = await ds.client.get(f"{BASE}/search?q=nothing")
    assert miss.json() == {"memories": []}

    # update
    res = await ds.client.post(f"{BASE}/{note_id}", json={"text": "navy blue"})
    assert res.status_code == 200
    assert res.json()["memory"]["text"] == "navy blue"

    # delete + confirm gone
    res = await ds.client.post(f"{BASE}/{note_id}/delete")
    assert res.json() == {"ok": True}
    assert (await ds.client.get(f"{BASE}/{note_id}")).status_code == 404


@pytest.mark.asyncio
async def test_create_replaces_on_duplicate_key(ds_memory):
    ds, _ = ds_memory
    r1 = await ds.client.post(BASE, json={"key": "k", "text": "v1"})
    r2 = await ds.client.post(BASE, json={"key": "k", "text": "v2"})
    assert r1.json()["memory"]["id"] == r2.json()["memory"]["id"]
    assert r2.json()["memory"]["text"] == "v2"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {"text": "missing key"},
        {"key": "missing_text"},
        {},
    ],
)
async def test_create_requires_key_and_text(ds_memory, body):
    ds, _ = ds_memory
    assert (await ds.client.post(BASE, json=body)).status_code == 400


@pytest.mark.asyncio
async def test_cross_actor_isolation_via_api():
    """A memory created by alice must be invisible + immutable to bob."""
    ds, _ = await setup_datasette(actor=None)
    alice = {"ds_actor": actor_cookie(ds, DEFAULT_ACTOR_ID)}
    bob = {"ds_actor": actor_cookie(ds, OTHER_ACTOR_ID)}

    # alice creates a memory
    r = await ds.client.post(
        BASE, json={"key": "secret", "text": "alice_only"}, cookies=alice
    )
    assert r.status_code == 200
    alice_id = r.json()["memory"]["id"]

    # bob sees nothing and cannot touch alice's row
    assert (await ds.client.get(BASE, cookies=bob)).json() == {"memories": []}
    assert (await ds.client.get(f"{BASE}/{alice_id}", cookies=bob)).status_code == 404
    assert (
        await ds.client.post(f"{BASE}/{alice_id}", json={"text": "hacked"}, cookies=bob)
    ).status_code == 404
    assert (
        await ds.client.post(f"{BASE}/{alice_id}/delete", cookies=bob)
    ).status_code == 404

    # alice's row is still intact
    r = await ds.client.get(f"{BASE}/{alice_id}", cookies=alice)
    assert r.json()["memory"]["text"] == "alice_only"


@pytest.mark.asyncio
async def test_method_not_allowed(ds_memory):
    """A method on a path with multiple handlers gets the 405 dispatcher.

    Single-method endpoints (e.g. `/<id>/delete`) return 404 on the
    wrong method — that's a deliberate limitation of the dispatcher.
    """
    ds, _ = ds_memory
    res = await ds.client.request("PUT", BASE)
    assert res.status_code == 405
    assert "GET" in res.headers["allow"]
    assert "POST" in res.headers["allow"]


@pytest.mark.asyncio
async def test_update_to_duplicate_key_returns_409(ds_memory):
    ds, _ = ds_memory
    await ds.client.post(BASE, json={"key": "a", "text": "first"})
    r = await ds.client.post(BASE, json={"key": "b", "text": "second"})
    b_id = r.json()["memory"]["id"]
    # Renaming b to a collides with the existing key.
    res = await ds.client.post(f"{BASE}/{b_id}", json={"key": "a"})
    assert res.status_code == 409
