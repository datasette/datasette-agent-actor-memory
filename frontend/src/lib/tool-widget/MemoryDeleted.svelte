<script lang="ts">
  import type { DeletedData } from "./types";
  import "./widget.css";

  let { data }: { data: DeletedData } = $props();
  const ok = $derived(data?.ok ?? false);
  const key = $derived(data?.key ?? "");
</script>

<div class="aam-widget aam-widget-deleted" class:aam-widget-noop={!ok}>
  <div class="aam-widget-head">
    <span class="aam-badge aam-badge-delete">
      {ok ? "Deleted" : "Not found"}
    </span>
    <code class="aam-key">{key}</code>
  </div>
  {#if !ok}
    <p class="aam-text aam-muted">
      No memory with that key existed — nothing was deleted.
    </p>
  {/if}
</div>
