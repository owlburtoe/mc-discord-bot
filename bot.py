import logging

import discord
from aiohttp import web
from discord.ext import commands

from config import settings
from crafty_api import CraftyClient

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
        self.crafty = await CraftyClient(
            settings.crafty_url, settings.crafty_token, settings.crafty_verify_ssl
        )

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

    async def start_health_server(self):
        async def health(_):
            return web.json_response(
                {
                    "status": "ok",
                    "servers": len(settings.servers),
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
