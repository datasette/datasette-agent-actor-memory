<script lang="ts">
  import type { ListData, Memory } from "./types";
  import "./widget.css";

  let { data }: { data: ListData } = $props();
  const memories: Memory[] = $derived(data?.memories ?? []);

  function fmt(ts: string): string {
    try {
      return new Date(ts).toLocaleString();
    } catch {
      return ts;
    }
  }
</script>

<div class="aam-widget aam-widget-list">
  <div class="aam-widget-head">
    <span class="aam-badge aam-badge-list">Memories</span>
    <span class="aam-count">{memories.length} total</span>
  </div>
  {#if memories.length === 0}
    <p class="aam-empty">No memories saved.</p>
  {:else}
    <ul class="aam-rows">
      {#each memories as m (m.id)}
        <li class="aam-row">
          <div class="aam-row-head">
            <code class="aam-key">{m.key}</code>
            <span class="aam-time" title={m.updated_at}>{fmt(m.updated_at)}</span>
          </div>
          <p class="aam-text">{m.text}</p>
        </li>
      {/each}
    </ul>
  {/if}
</div>
