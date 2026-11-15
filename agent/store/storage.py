"""Where the store's data lives: in memory, one fresh copy of `data/db.json` per conversation."""

from typing import Protocol

from agent.store.schema import WorkingDB


def dump_db(db: WorkingDB) -> str:
    # exclude_none keeps the data shaped exactly like the original db.json.
    return db.model_dump_json(exclude_none=True, indent=2)


class StorageBackend(Protocol):
    def load(self) -> WorkingDB: ...

    def save(self, db: WorkingDB) -> None: ...


class InMemoryBackend:
    """Keeps the last saved state as JSON, so a failed write can be rolled back."""

    def __init__(self, db: WorkingDB) -> None:
        self._saved = dump_db(db)

    def load(self) -> WorkingDB:
        return WorkingDB.model_validate_json(self._saved)

    def save(self, db: WorkingDB) -> None:
        self._saved = dump_db(db)
