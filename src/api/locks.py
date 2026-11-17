import asyncio
from contextlib import asynccontextmanager


class ThreadLocks:
    """One lock per conversation, so two requests on the same thread never interleave. Removed when unused."""

    def __init__(self):
        self._locks: dict[str, tuple[asyncio.Lock, int]] = {}

    @asynccontextmanager
    async def hold(self, key: str):
        lock, users = self._locks.get(key, (asyncio.Lock(), 0))
        self._locks[key] = (lock, users + 1)
        try:
            async with lock:
                yield
        finally:
            lock, users = self._locks[key]
            if users <= 1:
                del self._locks[key]
            else:
                self._locks[key] = (lock, users - 1)

    def size(self) -> int:
        return len(self._locks)
