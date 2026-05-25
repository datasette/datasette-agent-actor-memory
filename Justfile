DEV_PORT := "5173"
INTERNAL_DEV_DB := "/tmp/datasette-agent-actor-memory-dev-internal.db"
DEV_DATASETTE_PORT := "8001"

# --- Frontend build & dev ---

frontend *flags:
    npm run build --prefix frontend {{flags}}

frontend-dev *flags:
    npm run dev --prefix frontend -- --port {{DEV_PORT}} {{flags}}

# --- Formatting & checks ---

format-backend *flags:
    uv run --prerelease=allow ruff format {{flags}}

format-backend-check *flags:
    uv run --prerelease=allow ruff format --check {{flags}}

format:
    just format-backend

format-check:
    just format-backend-check

check-frontend:
    npm run check --prefix frontend

check-backend:
    uv run --prerelease=allow ruff check

check:
    just check-backend
    just check-frontend

# --- Tests ---

test *flags:
    uv run --prerelease=allow pytest {{flags}}

# --- Dev server ---

# Run datasette with the local plugin loaded, alongside sibling plugins
# that make the local agent stack usable. `--root` prints an auth-token
# URL on startup that grants the `root` actor — visit it once to bind
# the cookie and you can use the Memories UI.
#
# Memories live in Datasette's internal DB; pass `--internal <path>` so
# they persist across restarts. No user database needs to be attached.
#
# Memory tools have no `required_permission` — they are scoped to the
# authenticated actor at the data layer — so no permission grants are
# needed here.
dev *flags:
    DATASETTE_SECRET=abc123 uv run \
        --prerelease=allow \
        --with ../datasette-agent \
        --with ../datasette-agent-frontend \
        --with ../datasette-sidebar \
        --with ../datasette-user-profiles \
        --with llm-openrouter \
        datasette \
            --internal {{INTERNAL_DEV_DB}} \
            -p {{DEV_DATASETTE_PORT}} \
            --root \
            {{flags}}

# Hot-reload variant: watchexec restarts datasette on Python/HTML edits,
# and the vite dev server (run separately via `just frontend-dev`)
# serves the JS/CSS over HMR. `dev_paths` tells datasette-vite to
# resolve manifest entries against the vite dev origin instead of the
# built static files.
#
# Typical workflow: two terminals — `just frontend-dev` in one,
# `just dev-with-hmr` in the other.
dev-with-hmr *flags:
    watchexec \
        --stop-signal SIGKILL \
        -e py,html \
        --ignore '*.db' \
        --restart \
        --clear -- \
        just dev \
            -s plugins.datasette-vite.dev_paths.datasette_agent_actor_memory "http://localhost:{{DEV_PORT}}/-/static-plugins/datasette_agent_actor_memory/" \
            {{flags}}

# Wipe the dev internal DB. Useful when iterating on schema during
# development (migrations are append-only in production).
clean-dev-db:
    rm -f {{INTERNAL_DEV_DB}}
