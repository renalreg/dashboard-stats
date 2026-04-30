"""
Basic AI generated caching for functions which return dataframes.

Copy pasted from tableau extracts, to be replaced with something more fit for
purpose.
"""

from __future__ import annotations

import functools
import hashlib
import inspect
import json
from pathlib import Path
from typing import Any, Callable, Iterable, ParamSpec, TypeVar

import pandas as pd

P = ParamSpec("P")
R = TypeVar("R")


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]

    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}

    return repr(value)


def _make_cache_key(func: Callable[..., Any], payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode(
        "utf-8"
    )
    digest = hashlib.sha256(blob).hexdigest()[:16]
    return f"{func.__name__}__{digest}"


def cache_dataframe_to_disk(
    cache_dir: str | Path,
    *,
    exclude_params: Iterable[str] = (
        "session",
        "ukrdc_session",
        "archive_session",
        "engine",
        "connection",
        "conn",
    ),
    refresh: bool = False,
) -> Callable[[Callable[P, pd.DataFrame]], Callable[P, pd.DataFrame]]:
    cache_dir_path = Path(cache_dir)

    def decorator(func: Callable[P, pd.DataFrame]) -> Callable[P, pd.DataFrame]:
        signature = inspect.signature(func)
        exclude_set = set(exclude_params)

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> pd.DataFrame:
            bound = signature.bind_partial(*args, **kwargs)
            bound.apply_defaults()

            key_payload = {
                "func": func.__name__,
                "args": {
                    name: _jsonable(value)
                    for name, value in bound.arguments.items()
                    if name not in exclude_set
                },
            }
            cache_key = _make_cache_key(func, key_payload)

            cache_dir_path.mkdir(parents=True, exist_ok=True)
            cache_path = cache_dir_path / f"{cache_key}.pkl"

            if cache_path.exists() and not refresh:
                return pd.read_pickle(cache_path)

            df = func(*args, **kwargs)
            df.to_pickle(cache_path)
            return df

        return wrapper

    return decorator
