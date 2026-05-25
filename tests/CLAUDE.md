# tests/ — pytest

Backend tests. `pytest-asyncio` strict mode (configured in
`pyproject.toml`). Every test runs against a fresh in-memory Datasette
with the plugin's startup hook applied, so migrations have run before
the first request.

## Shared fixtures (`conftest.py`)

- `ds_memory` — `(Datasette, MemoryDB)` with `alice` bound as the
  default actor on `ds.client.get/post`. Pass
  `cookies={"ds_actor": ...}` to a single call to override.
- `ds_anon` — same Datasette, no default actor cookie. Use for the
  403 / login-redirect paths.
- `actor_cookie(ds, "...")` — a helper that signs an actor cookie
  outside of the monkey-patch path. Cross-actor isolation tests use
  this to switch between alice and bob on the same Datasette.

`OTHER_ACTOR_ID = "bob"` is the canonical second actor for isolation
tests.

## Patterns

**Two-actor isolation is the load-bearing test.** Any change to `db.py`
or `routes/memories.py` needs to keep cross-actor leaks impossible. The
DB-level test exhaustively checks the matrix (get / update / delete
by-id + by-key); the route-level test goes through HTTP. If you add a
new code path that touches memories, add a cross-actor assertion for it.

**Tool tests call `fn` directly**, not through the LLM harness. The
fixture-free helper `setup_datasette(actor=None)` lets each test build
its own Datasette and pass an explicit actor dict — useful because the
tool handlers take `actor` as a kwarg, not from a request.

**`_html` assertions are tag-existence checks, not snapshot tests.** The
Svelte bundle filename hash changes on every rebuild, so asserting on
"contains `<aam-memory-saved>`" or "contains `type=\"module\"`" beats
asserting on full output.

## Don't

- Don't grant any permissions in the test Datasette config — the tools
  have no `required_permission`, and the routes don't gate on actions.
  Granting things would mask a future regression where someone wires a
  permission check.
- Don't share a Datasette across actors via module-level fixtures.
  Per-test setup is cheap (in-memory + one migration step) and keeps
  tests isolated.
- Don't assert on the exact CSS/JS asset URL in `_html` — it's hashed.
- Don't drop the cross-actor isolation tests when refactoring `db.py`.
  Treat a failure there as a security bug, not a flake.
