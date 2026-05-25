from sqlite_utils import Database
from sqlite_migrate import Migrations

migrations = Migrations("datasette-agent-actor-memory")


async def ensure_migrations(database) -> None:
    """Apply pending migrations to *database* (idempotent).

    *database* is a Datasette ``Database`` (typically
    ``datasette.get_internal_database()``). Runs inside a write
    transaction via ``execute_write_fn`` so we hold the writer lock
    while sqlite-migrate inspects + applies steps.
    """

    def _apply(connection):
        migrations.apply(Database(connection))

    await database.execute_write_fn(_apply)


@migrations()
def m001_initial(db: Database):
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS _datasette_agent_actor_memory_note (
            id          INTEGER PRIMARY KEY NOT NULL,
            actor_id    TEXT    NOT NULL,
            key         TEXT    NOT NULL,
            text        TEXT    NOT NULL,
            created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            UNIQUE(actor_id, key)
        );
        CREATE INDEX IF NOT EXISTS idx_aam_note_actor
            ON _datasette_agent_actor_memory_note(actor_id);
        """
    )
