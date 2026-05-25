# datasette_agent_actor_memory/ — Python backend

Plugin runs against Datasette's internal database (`datasette --internal
<path>`). One table: `_datasette_agent_actor_memory_note`, with a
`UNIQUE(actor_id, key)` index that makes `save_memory` an upsert. File-level
docstrings cover purpose; this doc flags things you won't find by reading any
single file.

## Module map

- `__init__.py` — hookimpls. `register_routes`, `register_agent_tools`,
  `extra_template_vars` (delegates to `datasette_vite.vite_entry` for
  the page bundle), `menu_links`, `startup`. The `_method_dispatch_routes`
  helper collapses same-path GET/POST handlers into one method-dispatching
  wrapper, because Datasette matches the first regex hit. **The 405
  fallback only triggers when both methods are registered for a path** —
  single-method endpoints (e.g. `/delete`) return 404 on a wrong method,
  not 405.
- `router.py` — `Router()` instance imported everywhere route decorators
  live.
- `routes/memories.py` — every CRUD endpoint + the HTML page route.
  Anonymous requests get 403 (JSON API) or redirect to `/-/login` (HTML
  page). Path params (`note_id: int`) are coerced by datasette-plugin-router
  via runtime `is int` annotation inspection — see the file header.
- `db.py` — `MemoryDB` async wrapper. **Every method takes `actor_id` and
  every SQL has `WHERE actor_id = :aid`.** `upsert` uses
  `ON CONFLICT(actor_id, key) DO UPDATE`. `update_by_id` may raise
  `sqlite3.IntegrityError` on a key collision; routes translate that to 409.
- `migrations.py` — `sqlite-migrate` runner. Append-only; never edit a
  past `m00N_` step.
- `tools.py` — the four `AgentTool`s + the tool-widget rendering helpers.
  See "Tool rendering" below.
- `util.py` — `actor_id(request)` and `read_json_body`.

## Tool rendering

Each tool returns a JSON string with two layers:

- **Model-visible keys** (`memory`, `memories`, `ok`, …) — what the LLM sees.
- **`_html` key** — raw HTML rendered inline in the chat UI. Datasette-agent
  strips any top-level key whose name starts with `_` before forwarding the
  result to the model, so the model never sees the HTML.

`_widget_html(datasette, tag, payload)` composes
`<link>` + `<script type="module">` (from `vite_css_urls` /
`vite_js_urls` for the tool-widget entry) + the custom element with its
JSON payload child. The browser dedupes both module imports and stylesheet
URLs, so emitting these tags in every tool result is safe even when a
conversation contains many widgets.

Tag names map 1:1 to the four tools:
`aam-memory-saved`, `aam-memory-list`, `aam-memory-search`,
`aam-memory-deleted`. The Svelte custom elements live in
`frontend/src/lib/tool-widget/`.

## Routing

Routes are rooted at `/-/agents-actor-memory/...`. JSON API at
`/api/memories[/<id>][/delete|/search]`. HTML page at the root path.
Decorator-style `@router.GET/POST`; no PATCH/PUT/DELETE — verb-style POST
URLs (`/<id>/delete`) match what datasette-paper does.

## Permissions / actors

No registered actions. Tools have no `required_permission`. Access control
is *entirely* enforced by per-row `actor_id` matching in `db.py`. If you
ever add a `required_permission` to a tool, also register the action in
`__init__.py`'s `register_actions` hook (currently absent) and document the
expected `also_requires` relationships.

`actor_id(request)` returns `str(request.actor["id"])` or `None`. The
string form is what gets persisted, so an actor id `42` and `"42"` would
collide — fine in practice (Datasette actor ids are strings) but worth
knowing if you wire in a non-string id source.

## Don't

- Don't `from __future__ import annotations` in `routes/*.py`.
- Don't add a SELECT/UPDATE/DELETE in `db.py` without an `actor_id` filter.
  The tests cover cross-actor isolation; treat a failure there as a
  security regression, not flakiness.
- Don't grant a permission to bypass actor scoping. There is no admin role.
- Don't put HTML in non-underscore keys of a tool's JSON return — the LLM
  will see it and try to interpret it.
- Don't change a custom-element tag name without updating both the JS
  registration in `frontend/src/pages/tool-widget/main.ts` and the
  `_widget_html(... tag=...)` call site in `tools.py`.
