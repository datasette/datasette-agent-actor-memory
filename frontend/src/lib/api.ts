/**
 * Thin wrappers around the datasette-agent-actor-memory JSON API.
 * All endpoints rely on Datasette's actor cookie for auth.
 */

export type Memory = {
  id: number;
  actor_id: string;
  key: string;
  text: string;
  created_at: string;
  updated_at: string;
};

const BASE = "/-/agents-actor-memory/api/memories";

async function jsonOrThrow<T>(res: Response): Promise<T> {
  let body: any = null;
  try {
    body = await res.json();
  } catch {
    /* empty body */
  }
  if (!res.ok) {
    const msg = (body && body.error) || `${res.status} ${res.statusText}`;
    throw new Error(msg);
  }
  return body as T;
}

export async function listMemories(): Promise<Memory[]> {
  const res = await fetch(BASE, { credentials: "same-origin" });
  const { memories } = await jsonOrThrow<{ memories: Memory[] }>(res);
  return memories;
}

export async function searchMemories(q: string): Promise<Memory[]> {
  const url = `${BASE}/search?q=${encodeURIComponent(q)}`;
  const res = await fetch(url, { credentials: "same-origin" });
  const { memories } = await jsonOrThrow<{ memories: Memory[] }>(res);
  return memories;
}

export async function createMemory(
  key: string,
  text: string,
): Promise<Memory> {
  const res = await fetch(BASE, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key, text }),
  });
  const { memory } = await jsonOrThrow<{ memory: Memory }>(res);
  return memory;
}

export async function updateMemory(
  id: number,
  patch: { key?: string; text?: string },
): Promise<Memory> {
  const res = await fetch(`${BASE}/${id}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(patch),
  });
  const { memory } = await jsonOrThrow<{ memory: Memory }>(res);
  return memory;
}

export async function deleteMemory(id: number): Promise<void> {
  const res = await fetch(`${BASE}/${id}/delete`, {
    method: "POST",
    credentials: "same-origin",
  });
  await jsonOrThrow<{ ok: boolean }>(res);
}
