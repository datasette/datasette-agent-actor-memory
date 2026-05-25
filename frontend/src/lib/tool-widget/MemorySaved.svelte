<script lang="ts">
  import type { SavedData } from "./types";
  import "./widget.css";

  let { data }: { data: SavedData } = $props();
  const m = $derived(data?.memory);
</script>

{#if m}
  <div class="aam-widget aam-widget-saved">
    <div class="aam-widget-head">
      <span class="aam-badge aam-badge-save">Saved</span>
      <code class="aam-key">{m.key}</code>
    </div>
    <p class="aam-text">{m.text}</p>
  </div>
{:else}
  <div class="aam-widget aam-widget-error">Saved memory missing from payload</div>
{/if}
