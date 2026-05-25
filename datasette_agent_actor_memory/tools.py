"""Agent tools exposed to datasette-agent.

Tools return JSON strings. When the calling context renders rich HTML
(the chat UI), the JSON payload includes an ``_html`` key with the
custom-element markup for the tool-widget Svelte bundle. datasette-agent
strips any top-level ``_html`` (and any other underscore-prefixed key)
before forwarding the result to the LLM, so the visual rendering and the
model-visible payload are kept disjoint.
"""

from __future__ import annotations

import html
import json

from datasette_agent.tools import AgentTool
from datasette_vite import vite_css_urls, vite_js_urls

from .db import memory_db


PLUGIN_PACKAGE = "datasette_agent_actor_memory"
TOOL_WIDGET_ENTRY = "src/pages/tool-widget/main.ts"


def _require_actor_id(actor) -> str:
    aid = actor.get("id") if actor else None
    if not aid:
        raise PermissionError(
            "datasette-agent-actor-memory tools require an authenticated actor"
        )
    return str(aid)


def _widget_asset_tags(datasette) -> str:
    """Build the `<link>`/`<script>` tags for the tool-widget bundle.

    Uses datasette-vite's ``vite_js_urls`` + ``vite_css_urls`` so dev
    mode (``plugins.datasette-vite.dev_paths.datasette_agent_actor_memory``)
    routes through the Vite dev server and prod mode resolves the hashed
    filenames from the manifest.

    The browser dedupes module imports + stylesheet URLs, so emitting
    these tags inside every tool's ``_html`` is safe even when many
    widgets land in the same conversation.
    """
    parts: list[str] = []
    for href in vite_css_urls(
        datasette=datasette,
        entrypoint=TOOL_WIDGET_ENTRY,
        plugin_package=PLUGIN_PACKAGE,
    ):
        parts.append(f'<link rel="stylesheet" href="{html.escape(href)}">')
    for js in vite_js_urls(
        datasette=datasette,
        entrypoint=TOOL_WIDGET_ENTRY,
        plugin_package=PLUGIN_PACKAGE,
    ):
        url = html.escape(js["url"])
        if js.get("module"):
            parts.append(f'<script type="module" src="{url}"></script>')
        else:
            parts.append(f'<script src="{url}"></script>')
    return "\n".join(parts)


def _widget_html(datasette, tag: str, payload: dict) -> str:
    """Compose an inline tool-widget element + its JSON payload."""
    config_json = json.dumps(payload)
    # The JSON sits inside a `<script type="application/json">` so the
    # browser doesn't try to execute it, and HTML entities in the JSON
    # don't need escaping (the parser treats script contents as raw text)
    # — but we still must guard against a `</script>` substring inside
    # the payload, which would terminate the script tag.
    config_json = config_json.replace("</", "<\\/")
    return (
        f"{_widget_asset_tags(datasette)}\n"
        f"<{tag}>\n"
        f'<script type="application/json">{config_json}</script>\n'
        f"</{tag}>"
    )


async def _save_memory(datasette, actor, key, text):
    aid = _require_actor_id(actor)
    row = await memory_db(datasette).upsert(aid, key, text)
    return json.dumps(
        {
            "_html": _widget_html(datasette, "aam-memory-saved", {"memory": row}),
            "ok": True,
            "memory": row,
        }
    )


async def _list_memories(datasette, actor):
    aid = _require_actor_id(actor)
    rows = await memory_db(datasette).list_for_actor(aid)
    return json.dumps(
        {
            "_html": _widget_html(
                datasette, "aam-memory-list", {"memories": rows}
            ),
            "memories": rows,
        }
    )


async def _search_memories(datasette, actor, query):
    aid = _require_actor_id(actor)
    rows = await memory_db(datasette).search(aid, query)
    return json.dumps(
        {
            "_html": _widget_html(
                datasette,
                "aam-memory-search",
                {"query": query, "memories": rows},
            ),
            "query": query,
            "memories": rows,
        }
    )


async def _delete_memory(datasette, actor, key):
    aid = _require_actor_id(actor)
    deleted = await memory_db(datasette).delete_by_key(aid, key)
    return json.dumps(
        {
            "_html": _widget_html(
                datasette, "aam-memory-deleted", {"key": key, "ok": deleted}
            ),
            "ok": deleted,
        }
    )


TOOLS = [
    AgentTool(
        name="save_memory",
        description=(
            "Save (or replace) a short private note keyed by a stable identifier. "
            "Use a short snake_case key like 'preferred_editor' or 'home_city'. "
            "Saving again with the same key overwrites the previous value. "
            "Memories are private to the current user and never shared."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "Short stable identifier (snake_case recommended)",
                },
                "text": {
                    "type": "string",
                    "description": "The memory text to store",
                },
            },
            "required": ["key", "text"],
        },
        fn=_save_memory,
    ),
    AgentTool(
        name="list_memories",
        description=(
            "List all memories saved for the current user. Returns id, key, "
            "text, and timestamps for each memory."
        ),
        input_schema={"type": "object", "properties": {}},
        fn=_list_memories,
    ),
    AgentTool(
        name="search_memories",
        description=(
            "Substring search across the current user's memory keys and text. "
            "Use when you suspect a relevant memory exists but don't know its "
            "exact key."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Substring to match against keys and text",
                },
            },
            "required": ["query"],
        },
        fn=_search_memories,
    ),
    AgentTool(
        name="delete_memory",
        description=(
            "Delete a memory by its key. Returns ok=false if no such key "
            "exists for the current user."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The key of the memory to delete",
                },
            },
            "required": ["key"],
        },
        fn=_delete_memory,
    ),
]
