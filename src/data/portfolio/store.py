import logging

from src.data.portfolio import base
from src.data.portfolio.base import ConnectInfo
from src.data.portfolio.models import Holding

log = logging.getLogger(__name__)



class ConnectionStore:
    """Remembers, per thread, which portfolio sources are connected. One instance per (thread, source)."""

    def __init__(self, factories: dict[str, type] | None = None):
        self._factories = factories if factories is not None else base.SOURCES
        self._instances: dict[tuple[str, str], object] = {}
        self._connected: dict[str, list[str]] = {}
        self._pending: dict[str, str] = {}      # thread -> the question to answer once a source connects


    def options(self) -> list[tuple[str, str]]:
        return [(name, cls.label) for name, cls in self._factories.items()]

    def opened(self, thread_id: str) -> list[str]:
        """Sources with a live instance for this thread: connected ones AND logins still pending."""
        return [name for (tid, name) in self._instances if tid == thread_id]

    def set_pending(self, thread_id: str, question: str) -> None:
        self._pending[thread_id] = question

    def take_pending(self, thread_id: str) -> str | None:
        return self._pending.pop(thread_id, None)

    def clear_pending(self, thread_id: str) -> None:
        self._pending.pop(thread_id, None)


    def connected(self, thread_id: str) -> list[str]:
        return list(self._connected.get(thread_id, []))

    async def connect(self, thread_id: str, name: str, **params) -> ConnectInfo:
        if name not in self._factories:
            raise ValueError(f"unknown source '{name}'")
        key = (thread_id, name)
        if key not in self._instances:
            self._instances[key] = self._factories[name]()
        info = await self._instances[key].connect(**params)
        names = self._connected.setdefault(thread_id, [])
        if info.connected and name not in names:
            names.append(name)
        elif not info.connected and name in names:      # a failed (re)connect: the old session is gone
            names.remove(name)
        return info

    def disconnect(self, thread_id: str, name: str):
        """Forget the source and RETURN its instance so the caller can `await instance.close()` if it has one."""
        instance = self._instances.pop((thread_id, name), None)
        names = self._connected.get(thread_id, [])
        if name in names:
            names.remove(name)
        return instance

    async def close_all(self) -> None:
        """App shutdown: close every live connection (best effort) and forget everything."""
        for instance in list(self._instances.values()):
            close = getattr(instance, "close", None)
            if close:
                try:
                    await close()
                except Exception:
                    log.exception("closing a portfolio source failed")
        self._instances.clear()
        self._connected.clear()
        self._pending.clear()

    async def holdings(self, thread_id: str) -> list[Holding]:
        out: list[Holding] = []
        for name in self.connected(thread_id):
            out.extend(await self._instances[(thread_id, name)].holdings())
        return out
