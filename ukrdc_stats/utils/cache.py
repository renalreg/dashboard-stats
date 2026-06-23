"""
This module implements sqlalchemy specific caching for query results. The aim
of this is to reduce the round trips to the database. Replace the sessionmaker with the 
"""

import hashlib
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from dogpile.cache import make_region
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker

import portalocker
from dotenv import dotenv_values


# Load configuation for the cache from file
config_from_env = dotenv_values(".env")
CONFIG = {
    "expiration": int(config_from_env.get("CACHE_EXPIRATION", 3600)),
    "backend": config_from_env.get("CACHE_BACKEND", "file"),
    "cache_dir": Path(config_from_env.get("CACHE_DIR", ".do_not_commit")) / "query_cache",
    "redis_host": config_from_env.get("REDIS_HOST", "localhost"),
    "redis_port": int(config_from_env.get("REDIS_PORT", 6379)),
}

class WindowsFileLock:
    """Cross-platform file lock using portalocker (Windows-compatible)."""

    def __init__(self, filename: str):
        self.filename = filename
        self._filedesc = None

    def _open_lockfile(self) -> int:
        """Open lock file and return file descriptor."""
        import os
        return os.open(self.filename, os.O_CREAT | os.O_RDWR)

    def acquire_read_lock(self, wait: bool) -> bool:
        if self._filedesc is None:
            self._filedesc = self._open_lockfile()
        flag = portalocker.LOCK_SH | (0 if wait else portalocker.LOCK_NB)
        try:
            portalocker.lock(self._filedesc, flag)
            return True
        except portalocker.LockException:
            return False

    def acquire_write_lock(self, wait: bool) -> bool:
        if self._filedesc is None:
            self._filedesc = self._open_lockfile()
        flag = portalocker.LOCK_EX | (0 if wait else portalocker.LOCK_NB)
        try:
            portalocker.lock(self._filedesc, flag)
            return True
        except portalocker.LockException:
            return False

    def release_read_lock(self) -> None:
        if self._filedesc is not None:
            portalocker.unlock(self._filedesc)

    def release_write_lock(self) -> None:
        if self._filedesc is not None:
            portalocker.unlock(self._filedesc)

    def acquire(self, wait: bool = True) -> bool:
        """Generic acquire for dogpile mutex compatibility (uses write lock)."""
        return self.acquire_write_lock(wait)

    def release(self) -> None:
        """Generic release for dogpile mutex compatibility."""
        self.release_write_lock()

    def read(self):
        """Return context manager for read lock."""
        @contextmanager
        def _read_ctx():
            self.acquire_read_lock(True)
            try:
                yield self
            finally:
                self.release_read_lock()

        return _read_ctx()

    def write(self):
        """Return context manager for write lock."""
        @contextmanager
        def _write_ctx():
            self.acquire_write_lock(True)
            try:
                yield self
            finally:
                self.release_write_lock()

        return _write_ctx()


# Module-level cache region singleton
_cache_region = None


def _get_cache_region(config: dict) -> Any:
    """Create or return cached dogpile cache region."""
    global _cache_region
    if _cache_region is not None:
        return _cache_region

    backend = config.get("backend", "memory")

    if backend == "memory":
        _cache_region = make_region().configure("dogpile.cache.memory")
    elif backend == "file":
        cache_dir = config["cache_dir"]
        cache_dir.mkdir(parents=True, exist_ok=True)
        _cache_region = make_region().configure(
            "dogpile.cache.dbm",
            expiration_time=config.get("expiration", 3600),
            arguments={
                "filename": str(cache_dir / "query_cache.dbm"),
                "lock_factory": WindowsFileLock,
            },
        )
    elif backend == "redis":
        _cache_region = make_region().configure(
            "dogpile.cache.redis",
            expiration_time=config.get("expiration", 3600),
            arguments={
                "host": config.get("redis_host", "localhost"),
                "port": config.get("redis_port", 6379),
                "db": 0,
                "redis_expiration_time": config.get("expiration", 3600),
            },
        )
    else:
        raise ValueError(f"Unknown cache backend: {backend}")

    return _cache_region


def _generate_cache_key(
    url: URL, statement: Any, params: dict | None, fetch_method: str
) -> str:
    """The key needs to be unique for each database roundtrip.
    
    This is because the same query with different parameters should not be
    loaded from the cache.
    """
    
    sql_text = str(statement)
    parameters = params or {}

    key_parts = {
        "db": f"{url.host}{url.port}{url.database}",
        "sql": sql_text,
        "params": {k: str(v) for k, v in parameters.items()},
        "fetch": fetch_method,
    }
    blob = json.dumps(key_parts, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:32]


class CacheSession:
    """Wraps a SQLAlchemy Session with method interception via delegation.

    Unknown attributes/methods are passed through to the underlying session.
    Specific methods can be overridden to inject caching logic.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._url = session.bind.url

    def __getattr__(self, name: str) -> Any:
        """Pass through unknown attributes to the wrapped session."""
        return getattr(self._session, name)

    def execute(self, statement: Any, params: dict | None = None, **kwargs: Any) -> "CachedResult":
        """Execute with caching - returns CachedResult wrapping the actual result."""
        result = self._session.execute(statement, params, **kwargs)
        return CachedResult(result, self._url, statement, params) 

    def __enter__(self) -> "CacheSession":
        """Enter context manager - delegate to wrapped session."""
        self._session.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager - close the wrapped session."""
        self._session.close()


class CachedResult:
    """Wraps SQLAlchemy Result to cache fetch methods."""

    def __init__(
        self, result: Any, url: URL, statement: Any, params: dict | None
    ) -> None:
        self._result = result
        self._url = url
        self._statement = statement
        self._params = params

    def _fetch_with_cache(self, fetch_method: str, *args: Any, **kwargs: Any) -> Any:
        """Execute fetch method with caching via dogpile."""
        cache_key = _generate_cache_key(
            self._url, self._statement, self._params, fetch_method
        )
        region = _get_cache_region(CONFIG)

        def fetch_data():
            method = getattr(self._result, fetch_method)
            return method(*args, **kwargs)

        return region.get_or_create(cache_key, fetch_data)

    def all(self) -> Any:
        return self._fetch_with_cache("all")

    def first(self) -> Any:
        return self._fetch_with_cache("first")

    def one(self) -> Any:
        return self._fetch_with_cache("one")

    def one_or_none(self) -> Any:
        return self._fetch_with_cache("one_or_none")

    def __getattr__(self, name: str) -> Any:
        """Pass through other attributes to the wrapped result."""
        return getattr(self._result, name)


class CachedSessionMaker(sessionmaker):
    """Drop-in replacement for sessionmaker that returns CacheSession instances."""

    def __call__(self, **local_kw: Any) -> CacheSession:
        """Create a new Session and wrap it in CacheSession."""
        session = super().__call__(**local_kw)

        return CacheSession(session)

def cachedsessionmaker(**local_kw: Any):
    return CachedSessionMaker(**local_kw)
