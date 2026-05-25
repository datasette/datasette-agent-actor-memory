"""HTTP routes for datasette-agent-actor-memory.

Note: deliberately no ``from __future__ import annotations`` — datasette-plugin-router
inspects each handler's parameter annotations at runtime and uses
``param.annotation is int`` to decide how to extract path params. PEP 563
stringified annotations would silently break that check.
"""

import sqlite3

from datasette import Response

from ..db import memory_db
from ..router import router
from ..util import actor_id, read_json_body


def _forbidden() -> Response:
    return Response.json({"error": "auth required"}, status=403)


def _bad(msg: str, status: int = 400) -> Response:
    return Response.json({"error": msg}, status=status)


# ---------------------------------------------------------------------------
# HTML page
# ---------------------------------------------------------------------------


@router.GET(r"^/-/agents-actor-memory/?$")
async def memory_index_page(datasette, request):
    aid = actor_id(request)
    if not aid:
        # Match Datasette's default login URL convention.
        return Response.redirect("/-/login")
    return Response.html(
        await datasette.render_template(
            "agent_actor_memory_base.html",
            {
                "page_title": "Memories",
                "entrypoint": "src/pages/index/main.ts",
                "page_data": {"actor_id": aid},
            },
            request=request,
        )
    )


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------


@router.GET(r"^/-/agents-actor-memory/api/memories$")
async def list_memories(datasette, request):
    aid = actor_id(request)
    if not aid:
        return _forbidden()
    rows = await memory_db(datasette).list_for_actor(aid)
    return Response.json({"memories": rows})


@router.POST(r"^/-/agents-actor-memory/api/memories$")
async def create_memory(datasette, request):
    aid = actor_id(request)
    if not aid:
        return _forbidden()
    try:
        body = await read_json_body(request)
    except ValueError:
        return _bad("invalid JSON body")
    key = (body.get("key") or "").strip()
    text = body.get("text")
    if not key:
        return _bad("'key' is required")
    if text is None:
        return _bad("'text' is required")
    row = await memory_db(datasette).upsert(aid, key, text)
    return Response.json({"memory": row}, status=200)


@router.GET(r"^/-/agents-actor-memory/api/memories/search$")
async def search_memories(datasette, request):
    aid = actor_id(request)
    if not aid:
        return _forbidden()
    query = (request.args.get("q") or "").strip()
    if not query:
        return Response.json({"memories": []})
    rows = await memory_db(datasette).search(aid, query)
    return Response.json({"memories": rows})


@router.GET(r"^/-/agents-actor-memory/api/memories/(?P<note_id>\d+)$")
async def get_memory(datasette, request, note_id: int):
    aid = actor_id(request)
    if not aid:
        return _forbidden()
    row = await memory_db(datasette).get_by_id(aid, note_id)
    if row is None:
        return _bad("not found", status=404)
    return Response.json({"memory": row})


@router.POST(r"^/-/agents-actor-memory/api/memories/(?P<note_id>\d+)$")
async def update_memory(datasette, request, note_id: int):
    aid = actor_id(request)
    if not aid:
        return _forbidden()
    try:
        body = await read_json_body(request)
    except ValueError:
        return _bad("invalid JSON body")
    key = body.get("key")
    text = body.get("text")
    if key is None and text is None:
        return _bad("provide at least one of 'key' or 'text'")
    if key is not None:
        key = key.strip()
        if not key:
            return _bad("'key' must not be empty")
    try:
        row = await memory_db(datasette).update_by_id(
            aid, note_id, key=key, text=text
        )
    except sqlite3.IntegrityError:
        return _bad("a memory with that key already exists", status=409)
    if row is None:
        return _bad("not found", status=404)
    return Response.json({"memory": row})


@router.POST(r"^/-/agents-actor-memory/api/memories/(?P<note_id>\d+)/delete$")
async def delete_memory(datasette, request, note_id: int):
    aid = actor_id(request)
    if not aid:
        return _forbidden()
    deleted = await memory_db(datasette).delete_by_id(aid, note_id)
    if not deleted:
        return _bad("not found", status=404)
    return Response.json({"ok": True})
