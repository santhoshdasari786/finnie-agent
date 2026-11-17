import logging
from dataclasses import dataclass
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class Runtime:
    """Everything one running app needs: the compiled graph, the agents behind it, and the state to clean up."""
    graph: Any
    agents: dict
    store: Any
    memory: Any

    async def close(self) -> None:
        try:
            await self.store.close_all()          # closes live broker connections and their local callback servers
        except Exception:
            log.exception("closing connections failed")
