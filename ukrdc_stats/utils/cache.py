"""Session-level query caching."""

import hashlib
import json
from pathlib import Path
from contextlib import contextmanager
from typing import Literal

from dogpile.cache import make_region
from dogpile.cache.api import NO_VALUE
from sqlalchemy import event
from sqlalchemy.orm import Session

_DEFAULT_CACHE_DIR = Path(".do_not_commit") / "query_cache"

# Memory-based region (process lifetime)
_memory_region = make_region().configure("dogpile.cache.memory")


def _make_file_region(cache_dir: Path, expiration: int):
    """Create a dbm-backed file cache region."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    return make_region().configure(
        "dogpile.cache.dbm",
        expiration_time=expiration,
        arguments={"filename": str(cache_dir / "query_cache.dbm")},
    )

def _generate_cache_key(session: Session, statement, parameters: dict) -> str:
    """Hash of SQL structure + bound parameters + DB URL (no credentials)."""
    url = session.bind.url
    db_url = f"{url.drivername}://{url.host}:{url.port}/{url.database}"
    sql_text = str(statement._generate_cache_key())

    key_parts = {
        "db": db_url,
        "sql": sql_text,
        "params": {k: str(v) for k, v in parameters.items()},
    }
    blob = json.dumps(key_parts, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:32]

class QueryCache:
    """Caches query results."""

    def __init__(
        self,
        expiration: int = 3600,
        backend: Literal["memory", "file"] = "memory",
        cache_dir: Path = _DEFAULT_CACHE_DIR,
    ):
        self.expiration = expiration
        self._enabled = False
        self._region = (
            _make_file_region(cache_dir, expiration)
            if backend == "file"
            else _memory_region
        )
    
    def enable(self, session: Session):
        """Attach cache to this session."""
        self._enabled = True
        
        @event.listens_for(session, "do_orm_execute")
        def _on_orm_execute(orm_context):
            return self._intercept(orm_context)
    
    def _intercept(self, orm_context):
        """Check cache first, execute and store if not cached."""
        cache_key = _generate_cache_key(
            orm_context.session,
            orm_context.statement,
            orm_context.parameters or {}
        )

        cached = self._region.get(cache_key)
        if cached is not NO_VALUE:
            return cached()

        conn = orm_context.session.connection()
        result = conn.execute(orm_context.statement)
        frozen = result.freeze()
        self._region.set(cache_key, frozen)
        return frozen()


@contextmanager
def cached_session(
    session: Session,
    expiration: int = 3600,
    backend: Literal["memory", "file"] = "memory",
    cache_dir: Path = _DEFAULT_CACHE_DIR,
):
    """Context manager for query caching on a session.

    Args:
        backend: ``"memory"`` for in-process cache, ``"file"`` for a dbm file
            cache that persists between runs (stored in ``cache_dir``).
        cache_dir: Directory for the dbm file when ``backend="file"``.
    """
    cache = QueryCache(expiration, backend=backend, cache_dir=cache_dir)
    cache.enable(session)
    try:
        yield session
    finally:
        pass  # Events auto-detach when session closes