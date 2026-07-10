import logging
from dataclasses import dataclass, field

from crafty_api import CraftyClient

log = logging.getLogger("crafty-discord-bot.registry")

# A server entry is a plain {"id": ..., "name": ...} dict.
ServerEntry = dict[str, str]


@dataclass
class ServerDiff:
    """The set of servers added and removed between two refreshes."""

    added: list[ServerEntry] = field(default_factory=list)
    removed: list[ServerEntry] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed)


class ServerRegistry:
    """Caches the live server list from Crafty and exposes it to the bot.

    The cache is keyed by Crafty's UUID (unique; display names can collide). It is
    refreshed on a timer by the cog. On an API failure the previous cache is kept so
    the bot never goes blind on a transient outage.
    """

    def __init__(self, client: CraftyClient):
        self._client = client
        self._servers: dict[str, ServerEntry] = {}
        self.last_refresh_ok: bool = False
        self.last_refresh_error: str | None = None

    @property
    def servers(self) -> dict[str, ServerEntry]:
        """The current cache: {id: {"id", "name"}}."""
        return self._servers

    def seed(self, entries: dict[str, ServerEntry]) -> None:
        """Populate the cache from a fallback source without emitting a diff.

        Re-keys by each entry's ``id`` (config sources key by a short alias, not the
        UUID), so the cache stays consistent with what ``refresh`` produces.
        """
        self._servers = {e["id"]: {"id": e["id"], "name": e["name"]} for e in entries.values()}
        log.info("Seeded registry with %d server(s) from fallback source", len(self._servers))

    async def refresh(self) -> ServerDiff:
        """Re-pull the server list from Crafty and return what changed.

        On failure the existing cache is preserved and an empty diff is returned.
        """
        try:
            fetched = await self._client.list_servers()
        except Exception as e:
            self.last_refresh_ok = False
            self.last_refresh_error = str(e)
            log.warning("Server refresh failed, keeping last-known list: %s", e)
            return ServerDiff()

        new_cache = {entry["id"]: {"id": entry["id"], "name": entry["name"]} for entry in fetched}

        added = [v for sid, v in new_cache.items() if sid not in self._servers]
        removed = [v for sid, v in self._servers.items() if sid not in new_cache]

        self._servers = new_cache
        self.last_refresh_ok = True
        self.last_refresh_error = None

        if added or removed:
            log.info("Server refresh: +%d / -%d", len(added), len(removed))
        return ServerDiff(added=added, removed=removed)
