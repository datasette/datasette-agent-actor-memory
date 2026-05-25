<script lang="ts">
  import type { SearchData, Memory } from "./types";
  import "./widget.css";

  let { data }: { data: SearchData } = $props();
  const memories: Memory[] = $derived(data?.memories ?? []);
  const query = $derived(data?.query ?? "");

  function fmt(ts: string): string {
    try {
      return new Date(ts).toLocaleString();
    } catch {
      return ts;
    }
  }

  function highlight(text: string, q: string): { match: boolean; out: string } {
    if (!q) return { match: false, out: text };
    const idx = text.toLowerCase().indexOf(q.toLowerCase());
    if (idx === -1) return { match: false, out: text };
    return {
      match: true,
      out: text,
    };
  }
</script>

<div class="aam-widget aam-widget-search">
  <div class="aam-widget-head">
    <span class="aam-badge aam-badge-search">Search</span>
    <span class="aam-count">
      {memories.length} match{memories.length === 1 ? "" : "es"} for
      <code>{query}</code>
    </span>
  </div>
  {#if memories.length === 0}
    <p class="aam-empty">No memories matched.</p>
  {:else}
    <ul class="aam-rows">
      {#each memories as m (m.id)}
        {@const hl = highlight(m.text, query)}
        <li class="aam-row">
          <div class="aam-row-head">
            <code class="aam-key">{m.key}</code>
            <span class="aam-time" title={m.updated_at}>{fmt(m.updated_at)}</span>
          </div>
          <p class="aam-text" class:aam-text-match={hl.match}>{m.text}</p>
        </li>
      {/each}
    </ul>
  {/if}
</div>
