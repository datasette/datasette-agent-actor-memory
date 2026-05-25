/**
 * Tool-widget bundle for datasette-agent-actor-memory.
 *
 * Registers custom elements that the agent renders inline in chat. Each
 * tool handler emits HTML of the form:
 *
 *   <aam-memory-saved>
 *     <script type="application/json">{...payload...}</script>
 *   </aam-memory-saved>
 *
 * Datasette-agent picks the script tag and the surrounding element up
 * from the tool result's `_html` key.
 */

import { mount, unmount } from "svelte";
import MemorySaved from "../../lib/tool-widget/MemorySaved.svelte";
import MemoryList from "../../lib/tool-widget/MemoryList.svelte";
import MemorySearch from "../../lib/tool-widget/MemorySearch.svelte";
import MemoryDeleted from "../../lib/tool-widget/MemoryDeleted.svelte";

type SvelteComponentCtor = Parameters<typeof mount>[0];

function defineWidget(tagName: string, Component: SvelteComponentCtor): void {
  if (customElements.get(tagName)) return;

  class AamWidget extends HTMLElement {
    private app: ReturnType<typeof mount> | null = null;

    async connectedCallback() {
      let scriptEl = this.querySelector('script[type="application/json"]');
      if (!scriptEl) {
        // The script child can land after connectedCallback in some
        // insertion paths (innerHTML, fragment moves) — wait a frame
        // and retry. Mirrors datasette-agent-charts' DatasetteChart.
        await new Promise((r) => requestAnimationFrame(r));
        scriptEl = this.querySelector('script[type="application/json"]');
      }
      let data: unknown = {};
      if (scriptEl?.textContent) {
        try {
          data = JSON.parse(scriptEl.textContent);
        } catch (err) {
          this.innerHTML = `<div class="aam-widget aam-widget-error">Bad widget payload: ${String(err)}</div>`;
          return;
        }
      }
      this.innerHTML = "";
      const mountTarget = document.createElement("div");
      this.appendChild(mountTarget);
      this.app = mount(Component, {
        target: mountTarget,
        props: { data },
      });
    }

    disconnectedCallback() {
      if (this.app) {
        unmount(this.app);
        this.app = null;
      }
    }
  }

  customElements.define(tagName, AamWidget);
}

defineWidget("aam-memory-saved", MemorySaved as SvelteComponentCtor);
defineWidget("aam-memory-list", MemoryList as SvelteComponentCtor);
defineWidget("aam-memory-search", MemorySearch as SvelteComponentCtor);
defineWidget("aam-memory-deleted", MemoryDeleted as SvelteComponentCtor);
