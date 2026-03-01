import logging
from typing import Any

import aiohttp

log = logging.getLogger("crafty-discord-bot.api")


class CraftyClient:
    def __init__(self, url: str, token: str, verify_ssl: bool = True):
        self.url = url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        # Crafty sometimes uses self-signed certs
        self.connector = aiohttp.TCPConnector(ssl=None if verify_ssl else False)
        self.session = aiohttp.ClientSession(headers=self.headers, connector=self.connector)

    async def close(self):
        if self.session:
            await self.session.close()

    async def get_stats(self, server_id: str) -> dict[str, Any]:
        url = f"{self.url}/servers/{server_id}/stats"
        async with self.session.get(url, timeout=10) as r:
            r.raise_for_status()
            return await r.json()

    async def run_action(self, server_id: str, action: str) -> bool:
        url = f"{self.url}/servers/{server_id}/action/{action}"
        async with self.session.post(url, timeout=10) as r:
            return r.status in (200, 204)
