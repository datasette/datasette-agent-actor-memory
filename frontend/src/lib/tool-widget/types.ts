export type Memory = {
  id: number;
  actor_id: string;
  key: string;
  text: string;
  created_at: string;
  updated_at: string;
};

export type SavedData = { memory: Memory };
export type ListData = { memories: Memory[] };
export type SearchData = { query: string; memories: Memory[] };
export type DeletedData = { key: string; ok: boolean };
