import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import path from "path";

export default defineConfig({
  plugins: [svelte()],
  // Datasette serves datasette_agent_actor_memory/static/ at
  // /-/static-plugins/datasette_agent_actor_memory/. `datasette_vite.vite_entry`
  // strips the leading `static/` from manifest paths and resolves the rest
  // against that prefix.
  base: "/-/static-plugins/datasette_agent_actor_memory/",
  build: {
    target: "esnext",
    // outDir = plugin package root so `manifest.json` lands at
    // `datasette_agent_actor_memory/manifest.json` (where
    // `datasette_vite._load_manifest` looks for it), with assets nested
    // under `static/gen/`.
    outDir: path.resolve(__dirname, "../datasette_agent_actor_memory"),
    assetsDir: "static/gen",
    emptyOutDir: false,
    manifest: "manifest.json",
    rollupOptions: {
      input: {
        index: path.resolve(__dirname, "src/pages/index/main.ts"),
        // Tool-widget bundle: defines custom elements (<aam-memory-saved>,
        // <aam-memory-list>, <aam-memory-search>, <aam-memory-deleted>)
        // that the agent's tool-call handlers emit inline in chat via
        // the `_html` key. Kept in a separate entry so the chat UI only
        // loads what it needs.
        "tool-widget": path.resolve(
          __dirname,
          "src/pages/tool-widget/main.ts"
        ),
      },
    },
  },
  server: {
    port: 5173,
    strictPort: true,
    cors: true,
    origin: "http://localhost:5173",
    hmr: {
      host: "localhost",
      protocol: "ws",
    },
  },
});
