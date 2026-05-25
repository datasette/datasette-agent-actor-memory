"""Database operations for datasette-agent-actor-memory.

All memories live in Datasette's internal database in
``_datasette_agent_actor_memory_note``. Every query in this module is
scoped by ``actor_id`` — that is the security boundary that keeps memories
private. There is no admin or superuser bypass path.
"""

from __future__ import annotations


TABLE = "_datasette_agent_actor_memory_note"
_COLS = "id, actor_id, key, text, created_at, updated_at"


def _row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "actor_id": row["actor_id"],
        "key": row["key"],
        "text": row["text"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


class MemoryDB:
    """Thin async wrapper around Datasette's internal ``Database``."""

    def __init__(self, database) -> None:
        self.database = database

    async def list_for_actor(self, actor_id: str) -> list[dict]:
        result = await self.database.execute(
            f"SELECT {_COLS} FROM {TABLE} WHERE actor_id = :aid "
            "ORDER BY updated_at DESC, id DESC",
            {"aid": actor_id},
        )
        return [_row_to_dict(r) for r in result.rows]

    async def get_by_key(self, actor_id: str, key: str) -> dict | None:
        result = await self.database.execute(
            f"SELECT {_COLS} FROM {TABLE} WHERE actor_id = :aid AND key = :key",
            {"aid": actor_id, "key": key},
        )
        rows = list(result.rows)
        return _row_to_dict(rows[0]) if rows else None

    async def get_by_id(self, actor_id: str, note_id: int) -> dict | None:
        result = await self.database.execute(
            f"SELECT {_COLS} FROM {TABLE} WHERE actor_id = :aid AND id = :id",
            {"aid": actor_id, "id": note_id},
        )
        rows = list(result.rows)
        return _row_to_dict(rows[0]) if rows else None

    async def upsert(self, actor_id: str, key: str, text: str) -> dict:
        """Insert or replace the memory at (actor_id, key)."""
        sql = (
            f"INSERT INTO {TABLE} (actor_id, key, text) VALUES (:aid, :key, :text) "
            "ON CONFLICT(actor_id, key) DO UPDATE SET "
            "text = excluded.text, "
            "updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')"
        )
        await self.database.execute_write(
            sql, {"aid": actor_id, "key": key, "text": text}
        )
        row = await self.get_by_key(actor_id, key)
        assert row is not None
        return row

    async def update_by_id(
        self,
        actor_id: str,
        note_id: int,
        *,
        key: str | None = None,
        text: str | None = None,
    ) -> dict | None:
        """Update key and/or text on a row owned by *actor_id*.

        Returns the updated row, or ``None`` if no such row exists for
        this actor. Raises ``sqlite3.IntegrityError`` if *key* collides
        with another memory the actor already owns.
        """
        if key is None and text is None:
            return await self.get_by_id(actor_id, note_id)

        sets = []
        params: dict = {"aid": actor_id, "id": note_id}
        if key is not None:
            sets.append("key = :key")
            params["key"] = key
        if text is not None:
            sets.append("text = :text")
            params["text"] = text
        sets.append("updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')")

        sql = f"UPDATE {TABLE} SET {', '.join(sets)} WHERE actor_id = :aid AND id = :id"
        await self.database.execute_write(sql, params)
        return await self.get_by_id(actor_id, note_id)

    async def search(self, actor_id: str, query: str) -> list[dict]:
        """Substring search across this actor's keys + text."""
        like = f"%{query}%"
        result = await self.database.execute(
            f"SELECT {_COLS} FROM {TABLE} "
            "WHERE actor_id = :aid AND (key LIKE :like OR text LIKE :like) "
            "ORDER BY updated_at DESC, id DESC",
            {"aid": actor_id, "like": like},
        )
        return [_row_to_dict(r) for r in result.rows]

    async def delete_by_key(self, actor_id: str, key: str) -> bool:
        row = await self.get_by_key(actor_id, key)
        if row is None:
            return False
        await self.database.execute_write(
            f"DELETE FROM {TABLE} WHERE actor_id = :aid AND key = :key",
            {"aid": actor_id, "key": key},
        )
        return True

    async def delete_by_id(self, actor_id: str, note_id: int) -> bool:
        row = await self.get_by_id(actor_id, note_id)
        if row is None:
            return False
        await self.database.execute_write(
            f"DELETE FROM {TABLE} WHERE actor_id = :aid AND id = :id",
            {"aid": actor_id, "id": note_id},
        )
        return True


def memory_db(datasette) -> MemoryDB:
    return MemoryDB(datasette.get_internal_database())
