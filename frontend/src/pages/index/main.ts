import { mount } from "svelte";
import MemoryApp from "../../lib/MemoryApp.svelte";
import "../../app.css";

mount(MemoryApp, {
  target: document.getElementById("app-root")!,
  props: {},
});
