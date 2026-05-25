"""Shared helpers."""

from __future__ import annotations

import json


async def read_json_body(request) -> dict:
    body = await request.post_body()
    if not body:
        return {}
    return json.loads(body)


def actor_id(request) -> str | None:
    return str(request.actor.get("id")) if request.actor else None
