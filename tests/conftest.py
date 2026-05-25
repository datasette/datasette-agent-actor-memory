"""Shared pytest fixtures for datasette-agent-actor-memory.

The ``ds_memory`` fixture pre-binds a signed actor cookie for ``alice``
to every ``ds.client.get`` / ``ds.client.post`` call. Pass an explicit
``cookies={"ds_actor": ...}`` to a client call to override (or to make
truly anonymous requests).
"""

from __future__ import annotations

import pytest_asyncio
from datasette.app import Datasette

from datasette_agent_actor_memory.db import MemoryDB


DEFAULT_ACTOR_ID = "alice"
OTHER_ACTOR_ID = "bob"


def make_datasette() -> Datasette:
    return Datasette(memory=True)


def _bind_actor(ds: Datasette, actor_id: str) -> None:
    """Inject a default ``ds_actor`` cookie on every client call."""
    cookie = ds.sign({"a": {"id": actor_id}}, "actor")
    orig_get = ds.client.get
    orig_post = ds.client.post

    def _merge(kwargs):
        cookies = dict(kwargs.get("cookies") or {})
        cookies.setdefault("ds_actor", cookie)
        kwargs["cookies"] = cookies
        return kwargs

    async def _get(path, **kw):
        return await orig_get(path, **_merge(kw))

    async def _post(path, **kw):
        return await orig_post(path, **_merge(kw))

    ds.client.get = _get  # type: ignore[method-assign]
    ds.client.post = _post  # type: ignore[method-assign]


def actor_cookie(ds: Datasette, actor_id: str) -> str:
    return ds.sign({"a": {"id": actor_id}}, "actor")


async def setup_datasette(*, actor: str | None = DEFAULT_ACTOR_ID):
    ds = make_datasette()
    await ds.invoke_startup()
    if actor is not None:
        _bind_actor(ds, actor)
    return ds, MemoryDB(ds.get_internal_database())


@pytest_asyncio.fixture
async def ds_memory():
    """Yield ``(datasette, MemoryDB)`` with alice's cookie bound."""
    ds, db = await setup_datasette()
    yield ds, db


@pytest_asyncio.fixture
async def ds_anon():
    """Yield a Datasette with no actor cookie bound (anonymous requests)."""
    ds, db = await setup_datasette(actor=None)
    yield ds, db


@pytest_asyncio.fixture
async def db():
    """Yield a bare ``MemoryDB`` — for tests that only need the data layer."""
    _, db_ = await setup_datasette(actor=None)
    yield db_


@pytest_asyncio.fixture
async def ds_tools():
    """Yield a Datasette suitable for calling tool ``fn``s directly.

    Tools take ``actor`` as a kwarg, so the client-cookie monkey-patch
    isn't useful here — each test passes the actor dict it wants.
    """
    ds, _ = await setup_datasette(actor=None)
    yield ds
