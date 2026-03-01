import logging
from typing import Any

import aiohttp

log = logging.getLogger("crafty-discord-bot.api")


class CraftyClient:
    def __init__(self, url: str, token: str, session: aiohttp.ClientSession | None = None):
        self.url = url.rstrip("/")
        self.token = token
        self._session = session
        self._own_session = False

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                }
            )
            self._own_session = True
        return self._session

    async def close(self):
        if self._own_session and self._session:
            await self._session.close()

    async def get_stats(self, server_id: str) -> dict[str, Any]:
        url = f"{self.url}/servers/{server_id}/stats"
        session = await self._get_session()
        async with session.get(url, timeout=10) as r:
            r.raise_for_status()
            return await r.json()

    async def run_action(self, server_id: str, action: str) -> bool:
        url = f"{self.url}/servers/{server_id}/action/{action}"
        session = await self._get_session()
        async with session.post(url, timeout=10) as r:
            return r.status in (200, 204)
