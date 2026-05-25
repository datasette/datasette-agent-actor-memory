# frontend/ — Vite + Svelte 5

Two Vite entries, one shared `outDir`:

- **`src/pages/index/main.ts`** — the `/-/agents-actor-memory/` UI page.
  Mounts `MemoryApp.svelte` into `#app-root` in the
  `agent_actor_memory_base.html` template. Injected by
  `datasette_vite.vite_entry`.
- **`src/pages/tool-widget/main.ts`** — registers custom elements
  (`<aam-memory-saved>`, `<aam-memory-list>`, `<aam-memory-search>`,
  `<aam-memory-deleted>`) that the four agent tools emit inline in chat
  via the `_html` key. The Python side derives this bundle's URL via
  `vite_js_urls` + `vite_css_urls` in `tools.py`.

Each entry's chunk is hashed at build time and resolved through the
manifest at `datasette_agent_actor_memory/manifest.json` (or via
`plugins.datasette-vite.dev_paths.datasette_agent_actor_memory` in dev).

## Where things live

- `vite.config.ts` — `outDir: ../datasette_agent_actor_memory`,
  `assetsDir: static/gen`, `manifest: manifest.json`,
  `base: /-/static-plugins/datasette_agent_actor_memory/`. Two rollup
  inputs (the two entries above).
- `src/lib/MemoryApp.svelte` — the page UI. Reads `actor_id` from the
  embedded `pageData` blob, then drives the JSON API at
  `/-/agents-actor-memory/api/memories[/<id>][/delete|/search]` via the
  `api.ts` wrappers.
- `src/lib/api.ts` — typed `fetch` wrappers. All calls use
  `credentials: "same-origin"` so the actor cookie attaches.
- `src/lib/tool-widget/*.svelte` — one component per custom element.
  All four import the shared `widget.css` so the bundle ships a single
  stylesheet.
- `src/lib/tool-widget/main.ts`'s `defineWidget` reads the
  `<script type="application/json">` child of the element, parses it,
  then mounts the Svelte component with `data` as a prop.

## Conventions that bite

- **`const x = data?.foo` in a Svelte 5 component is a runtime warning.**
  Use `const x = $derived(data?.foo)`. Prop destructuring at the top is
  fine; derived computations from a prop must go through `$derived`.
- **Custom-element children can land *after* `connectedCallback`.** When
  the agent UI inserts `_html` via `innerHTML`, the inner
  `<script type="application/json">` is sometimes not parsed yet. The
  `defineWidget` helper retries once after a `requestAnimationFrame` —
  preserve that fallback if you refactor.
- **The script-tag JSON payload is escaped with `</` → `<\/`.** A
  `</script>` substring in any memory text would otherwise terminate
  the tag. The browser parses the escaped form back to the original.
- **The Svelte custom elements are *not* shadow-DOM web components.**
  `defineWidget` wraps a plain `HTMLElement` and mounts the Svelte
  component into a child div, so the page's CSS cascades in normally.
  If you ever need shadow DOM, `<svelte:options customElement>` is the
  switch.

## Dev / build

```
npm install
npm run build           # writes hashed bundles + manifest into ../datasette_agent_actor_memory
npm run dev             # Vite dev server on :5173 (pair with just dev-with-hmr)
npm run check           # svelte-check
```

## Don't

- Don't merge a new tool widget without registering its tag in
  `defineWidget` *and* updating the matching `_widget_html(..., tag=...)`
  call site in `tools.py`. The Python helper happily emits a tag the
  browser doesn't know.
- Don't import the page bundle's CSS from a tool-widget component (or
  vice versa). They're separate entries so each renders standalone.
- Don't reach into `MemoryApp.svelte` from a tool widget — the widgets
  render inside the agent's chat UI on a totally different page.
