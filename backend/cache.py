"""
A deliberately simple TTL cache: a module-level dict survives for the
lifetime of a warm container/process, which is enough to keep a 10-league
scan from re-fetching on every request within the TTL window. On a cold
start it's just empty again -- that's fine, it costs one extra scan.
"""
import time

_store: dict = {}


def cache_get(key: str):
    entry = _store.get(key)
    if entry is None:
        return None

    expires_at, value = entry
    if time.time() > expires_at:
        del _store[key]
        return None

    return value


def cache_set(key: str, value, ttl_seconds: int) -> None:
    _store[key] = (time.time() + ttl_seconds, value)
