import logging

import discord
from aiohttp import web
from discord.ext import commands

from config import settings
from crafty_api import CraftyClient
from server_registry import ServerRegistry

# ======================
# Logging
# ======================
logging.basicConfig(
    level=settings.log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
log = logging.getLogger("crafty-discord-bot")


# ======================
# Bot class
# ======================
class CraftyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        # self.crafty will be initialized in setup_hook as it's an awaitable call

    async def setup_hook(self):
        # Initialize CraftyClient here as it's an awaitable call
        self.crafty = CraftyClient(
            settings.crafty_url, settings.crafty_token, settings.crafty_verify_ssl
        )

        # Registry: live server list auto-discovered from Crafty
        self.registry = ServerRegistry(self.crafty)
        await self.initial_server_load()

        # Load Cogs
        await self.load_extension("cogs.minecraft")

        await self.start_health_server()

        # sync slash commands
        if settings.guild_id:
            guild = discord.Object(id=int(settings.guild_id))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("Synced %s guild commands", len(synced))
        else:
            synced = await self.tree.sync()
            log.info("Synced %s global commands", len(synced))

    async def initial_server_load(self):
        """Populate the registry at startup.

        Pull from Crafty first. If Crafty is unreachable and we have no cache, fall back
        to the optional servers.json / MC_SERVERS_JSON seed so the bot is still usable
        offline until the periodic refresh succeeds.
        """
        await self.registry.refresh()
        if not self.registry.last_refresh_ok and not self.registry.servers:
            seed = settings.servers
            if seed:
                log.warning(
                    "Crafty unreachable at startup; seeding %d server(s) from file", len(seed)
                )
                self.registry.seed(seed)

    async def start_health_server(self):
        async def health(_):
            return web.json_response(
                {
                    "status": "ok",
                    "servers": len(self.registry.servers),
                    "last_refresh_ok": self.registry.last_refresh_ok,
                }
            )

        app = web.Application()
        app.router.add_get("/health", health)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8080)
        await site.start()

        log.info("Health endpoint started on :8080/health")

    async def close(self):
        await super().close()
        await self.crafty.close()


bot = CraftyBot()


# ======================
# Events
# ======================
@bot.event
async def on_ready():
    log.info("Bot online | user=%s id=%s", bot.user, bot.user.id)


# ======================
# Entrypoint
# ======================
if __name__ == "__main__":
    bot.run(settings.discord_token)
