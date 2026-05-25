# datasette-agent-actor-memory

Datasette plugin: per-actor private long-term memory for
[`datasette-agent`](https://github.com/datasette/datasette-agent). Tools
let an agent `save_memory`, `list_memories`, `search_memories`,
`delete_memory` for the current actor; a Svelte UI at
`/-/agents-actor-memory/` mirrors that with full CRUD. All memories live
in Datasette's internal DB, scoped by `actor_id` at every query — there
is no admin/superuser bypass.

## Where things live

- `datasette_agent_actor_memory/` — Python plugin. See
  `datasette_agent_actor_memory/CLAUDE.md`.
- `frontend/` — Svelte 5 + Vite. Two entries: the page UI and the
  tool-widget custom elements. See `frontend/CLAUDE.md`.
- `tests/` — pytest + `pytest-asyncio`. See `tests/CLAUDE.md`.

File-level docstrings cover most "what does this module do" questions;
this doc only flags things you wouldn't find by reading any one file.

## Cross-cutting load-bearing rules

1. **Actor scoping is the *only* access control.** Every SQL statement
   in `db.py` filters `WHERE actor_id = :aid`. Bypass this and you leak
   memories across users. No admin grant, no superuser flag.
2. **No `from __future__ import annotations` in
   `datasette_agent_actor_memory/routes/*.py`.**
   `datasette-plugin-router` uses `param.annotation is int` at runtime;
   PEP 563 stringifies annotations and silently breaks path-param
   coercion. (The route file has a header comment about this.)
3. **Migrations are append-only** (`migrations.py`). Add a new
   `m00N_` step, never edit a past one.
4. **Underscore-prefix keys in tool JSON are stripped before the LLM
   sees them.** `_html` is the chat-only rich rendering channel; the
   non-underscore keys are what the model gets. Keep them disjoint.
5. **Build before exercising the chat widgets or the UI page.**
   `datasette_vite.vite_entry` and `vite_js_urls` read the manifest at
   the package root; without `npm run build` (or the Vite dev server +
   `dev_paths`) the manifest is missing and rendering 500s.

## Development

```
npm install --prefix frontend
just frontend            # build the bundle
just dev                 # datasette with sibling agent plugins + --root token
just dev-with-hmr        # watchexec restart + Vite dev origin for HMR
just test                # backend pytest
```

For HMR: in one terminal `just frontend-dev`, in another
`just dev-with-hmr`. The HMR recipe wires
`plugins.datasette-vite.dev_paths.datasette_agent_actor_memory` so both
the page UI *and* the tool-widget bundle resolve through the Vite dev
server.

Always run Python via `uv run --prerelease=allow …` — Datasette is on
the `>1a` pre-release pin.

## Before every commit

```
just format-backend
just check-backend
just check-frontend
just test
```

If `format-backend` rewrites files, re-stage. If you touch the Svelte
widgets or `tools.py`'s `_html` builder, also `just frontend` to refresh
the bundle (tests assert the rendered tag names).
