<script lang="ts">
  import { onMount } from "svelte";
  import {
    listMemories,
    searchMemories,
    createMemory,
    updateMemory,
    deleteMemory,
    type Memory,
  } from "./api";

  type PageData = { actor_id: string | null };

  function loadPageData(): PageData {
    const el = document.getElementById("pageData");
    if (!el) return { actor_id: null };
    try {
      return JSON.parse(el.textContent || "{}") as PageData;
    } catch {
      return { actor_id: null };
    }
  }

  const page = loadPageData();

  let memories = $state<Memory[]>([]);
  let loading = $state(false);
  let error = $state<string | null>(null);

  let searchQuery = $state("");
  let searchTimer: ReturnType<typeof setTimeout> | undefined;

  let newKey = $state("");
  let newText = $state("");
  let creating = $state(false);

  // Per-row edit state, keyed by memory id.
  let editingId = $state<number | null>(null);
  let editKey = $state("");
  let editText = $state("");
  let busyId = $state<number | null>(null);

  async function refresh() {
    loading = true;
    error = null;
    try {
      memories = searchQuery.trim()
        ? await searchMemories(searchQuery.trim())
        : await listMemories();
    } catch (e) {
      error = (e as Error).message;
    } finally {
      loading = false;
    }
  }

  function onSearchInput() {
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(refresh, 200);
  }

  async function onCreate() {
    if (!newKey.trim() || !newText) return;
    creating = true;
    error = null;
    try {
      await createMemory(newKey.trim(), newText);
      newKey = "";
      newText = "";
      await refresh();
    } catch (e) {
      error = (e as Error).message;
    } finally {
      creating = false;
    }
  }

  function startEdit(m: Memory) {
    editingId = m.id;
    editKey = m.key;
    editText = m.text;
  }

  function cancelEdit() {
    editingId = null;
    editKey = "";
    editText = "";
  }

  async function saveEdit(m: Memory) {
    if (!editKey.trim()) return;
    busyId = m.id;
    error = null;
    try {
      await updateMemory(m.id, { key: editKey.trim(), text: editText });
      cancelEdit();
      await refresh();
    } catch (e) {
      error = (e as Error).message;
    } finally {
      busyId = null;
    }
  }

  async function onDelete(m: Memory) {
    if (!confirm(`Delete memory "${m.key}"?`)) return;
    busyId = m.id;
    error = null;
    try {
      await deleteMemory(m.id);
      if (editingId === m.id) cancelEdit();
      await refresh();
    } catch (e) {
      error = (e as Error).message;
    } finally {
      busyId = null;
    }
  }

  function fmt(ts: string): string {
    try {
      return new Date(ts).toLocaleString();
    } catch {
      return ts;
    }
  }

  onMount(refresh);
</script>

<div class="aam-app">
  <h1>Memories</h1>
  <div class="aam-meta">
    {#if page.actor_id}
      Private to <code>{page.actor_id}</code>. Not shared with other users.
    {:else}
      Sign in to manage memories.
    {/if}
  </div>

  {#if error}
    <div class="aam-error">{error}</div>
  {/if}

  <div class="aam-new">
    <label>
      Key
      <input
        type="text"
        placeholder="snake_case_key"
        bind:value={newKey}
        disabled={creating}
      />
    </label>
    <label>
      Text
      <textarea
        placeholder="What should I remember?"
        bind:value={newText}
        disabled={creating}
      ></textarea>
    </label>
    <div class="aam-new-actions">
      <button
        class="primary"
        onclick={onCreate}
        disabled={creating || !newKey.trim() || !newText}
      >
        {creating ? "Saving…" : "Save memory"}
      </button>
      <small>Saving an existing key replaces the previous value.</small>
    </div>
  </div>

  <input
    class="aam-search"
    type="search"
    placeholder="Search memories…"
    bind:value={searchQuery}
    oninput={onSearchInput}
  />

  {#if loading}
    <p>Loading…</p>
  {:else if memories.length === 0}
    <p class="aam-empty">
      {searchQuery.trim()
        ? "No memories match that search."
        : "No memories yet — save one above, or ask an agent to remember something."}
    </p>
  {:else}
    <ul class="aam-list">
      {#each memories as m (m.id)}
        <li class="aam-row">
          {#if editingId === m.id}
            <div class="aam-edit">
              <input type="text" bind:value={editKey} />
              <textarea bind:value={editText}></textarea>
              <div class="aam-row-actions">
                <button
                  class="primary"
                  onclick={() => saveEdit(m)}
                  disabled={busyId === m.id || !editKey.trim()}
                >
                  Save
                </button>
                <button onclick={cancelEdit} disabled={busyId === m.id}>
                  Cancel
                </button>
              </div>
            </div>
          {:else}
            <div class="aam-row-head">
              <span class="aam-row-key">{m.key}</span>
              <span class="aam-row-time" title={m.updated_at}>
                {fmt(m.updated_at)}
              </span>
            </div>
            <p class="aam-row-text">{m.text}</p>
            <div class="aam-row-actions">
              <button onclick={() => startEdit(m)} disabled={busyId === m.id}>
                Edit
              </button>
              <button
                class="danger"
                onclick={() => onDelete(m)}
                disabled={busyId === m.id}
              >
                Delete
              </button>
            </div>
          {/if}
        </li>
      {/each}
    </ul>
  {/if}
</div>
