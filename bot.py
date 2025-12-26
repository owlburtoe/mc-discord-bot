import os
import asyncio
import aiohttp
import logging
import discord
from discord import app_commands
from discord.ext import commands
from aiohttp import web


# ======================
# Logging
# ======================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

log = logging.getLogger("crafty-discord-bot")


# ======================
# Environment variables
# ======================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

CRAFTY_URL = os.getenv("CRAFTY_URL", "").rstrip("/")
CRAFTY_TOKEN = os.getenv("CRAFTY_TOKEN")

ALLOWED_CHANNEL_ID = int(os.getenv("ALLOWED_CHANNEL_ID", "0"))
GUILD_ID = os.getenv("GUILD_ID")

OWNER_ID = int(os.getenv("OWNER_ID", "0"))
MOD_ROLE_ID = int(os.getenv("MOD_ROLE_ID", "0"))

# optional: restrict-visible servers
ALLOWLIST = os.getenv("CRAFTY_SERVER_ALLOWLIST")
if ALLOWLIST:
    ALLOWLIST = {x.strip() for x in ALLOWLIST.split(",")}
else:
    ALLOWLIST = None


# ======================
# Load server definitions from env
# ======================
servers = {}

for i in range(1, 20):
    key = os.getenv(f"MC_SERVER_{i}_KEY")
    name = os.getenv(f"MC_SERVER_{i}_NAME")
    uuid = os.getenv(f"MC_SERVER_{i}_ID")

    if not key or not uuid:
        continue

    servers[key.lower()] = {
        "name": name or key,
        "id": uuid,
    }

bot_key_map = servers  # key -> {name, id}


# ======================
# Bot class
# ======================
class CraftyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

        self.session: aiohttp.ClientSession | None = None
        self.servers: dict[str, str] = {}

    async def setup_hook(self):
        # HTTP session
        self.session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {CRAFTY_TOKEN}",
                "Content-Type": "application/json",
            }
        )

        await self.start_health_server()

        # sync slash commands
        if GUILD_ID:
            guild = discord.Object(id=int(GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("Synced %s guild commands", len(synced))
        else:
            synced = await self.tree.sync()
            log.info("Synced %s global commands", len(synced))

    async def start_health_server(self):
        async def health(_):
            return web.json_response({
                "status": "ok",
                "servers": len(self.servers),
            })

        app = web.Application()
        app.router.add_get("/health", health)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8080)
        await site.start()

        log.info("Health endpoint started on :8080/health")

    async def close(self):
        await super().close()
        if self.session:
            await self.session.close()


bot = CraftyBot()

bot.servers = {v["name"]: v["id"] for v in bot_key_map.values()}
bot.server_keys = bot_key_map

# ======================
# Permission helpers
# ======================
async def is_mod(interaction: discord.Interaction) -> bool:
    if interaction.user.id == OWNER_ID:
        return True

    if not interaction.guild:
        return False

    member = interaction.guild.get_member(interaction.user.id)
    if not member:
        return False

    if MOD_ROLE_ID:
        return any(role.id == MOD_ROLE_ID for role in member.roles)

    return False


async def validate_context(interaction: discord.Interaction, restricted: bool = False):
    if ALLOWED_CHANNEL_ID and interaction.channel.id != ALLOWED_CHANNEL_ID:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🚫 Wrong channel",
                description=f"Use <#{ALLOWED_CHANNEL_ID}> for this command.",
                color=discord.Color.red(),
            ),
            ephemeral=True,
        )
        return False

    if restricted and not await is_mod(interaction):
        await interaction.response.send_message(
            embed=discord.Embed(
                title="⛔ Permission denied",
                description="You are not allowed to perform that action.",
                color=discord.Color.red(),
            ),
            ephemeral=True,
        )
        return False

    return True


# ======================
# Autocomplete helper
# ======================
async def server_autocomplete(interaction: discord.Interaction, current: str):
    choices = []
    for key, entry in bot.server_keys.items():
        name = entry.get("name", key)
        if current.lower() in name.lower():
            choices.append(app_commands.Choice(name=name, value=name))
    return choices[:25]


# ======================
# Main slash command
# ======================
@bot.tree.command(name="mc", description="Query or control Crafty Minecraft servers")
@app_commands.describe(server="Server name", action="Action to perform")
@app_commands.choices(
    action=[
        app_commands.Choice(name="📊 Status", value="status"),
        app_commands.Choice(name="🟢 Start", value="start_server"),
        app_commands.Choice(name="🛑 Stop", value="stop_server"),
        app_commands.Choice(name="🔁 Restart", value="restart_server"),
    ]
)
@app_commands.autocomplete(server=server_autocomplete)
async def mc_manager(
    interaction: discord.Interaction,
    server: str,
    action: app_commands.Choice[str],
):
    log.info(
        "mc_ctl invoked | user=%s server=%s action=%s",
        interaction.user,
        server,
        action.value,
    )

    is_admin_action = action.value != "status"

    if not await validate_context(interaction, restricted=is_admin_action):
        return

    entry = None
    for v in bot.server_keys.values():
        if v.get("name", "").lower() == server.lower():
            entry = v
            break

    if not entry:
        await interaction.response.send_message(
            embed=discord.Embed(
                title="❌ Unknown server",
                description=f"`{server}` was not found.",
                color=discord.Color.red(),
            ),
            ephemeral=True,
        )
        return

    server_id = entry["id"]
    server_display_name = entry["name"]

    await interaction.response.defer(thinking=True)

    try:

# STATUS QUERY
        if action.value == "status":
            url = f"{CRAFTY_URL}/servers/{server_id}/stats"

            async with bot.session.get(url, timeout=10) as r:
                data = await r.json()

            d = data.get("data", {})
            running = d.get("running", False)

            status_emoji = "🟢" if running else "🔴"
            status_label = "ONLINE" if running else "OFFLINE"

            players_online = d.get("online", 0)
            players_max = d.get("max", 0)

            embed = discord.Embed(
                title=f"{status_emoji} {server_display_name}",
                color=discord.Color.green() if running else discord.Color.red(),
            )

            embed.add_field(name="Status", value=f"**{status_label}**", inline=True)
            embed.add_field(
                name="Players",
                value=f"`{players_online}/{players_max}`",
                inline=True,
            )

            await interaction.followup.send(embed=embed)
            return

        # CONTROL ACTIONS
        emoji_map = {
            "start_server": "🟢",
            "stop_server": "🛑",
            "restart_server": "🔁",
        }

        verb_map = {
            "start_server": "Start",
            "stop_server": "Stop",
            "restart_server": "Restart",
        }

        control_url = f"{CRAFTY_URL}/servers/{server_id}/action/{action.value}"

        async with bot.session.post(control_url, timeout=10) as r:
            if r.status in (200, 204):
                embed = discord.Embed(
                    title=f"{emoji_map.get(action.value, '⚙️')} {verb_map.get(action.value)} sent",
                    description=f"Command sent to **{server_display_name}**.",
                    color=discord.Color.blurple(),
                )
                await interaction.followup.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="⚠️ Crafty API error",
                    description=f"Returned HTTP `{r.status}`.",
                    color=discord.Color.orange(),
                )
                await interaction.followup.send(embed=embed)

    except Exception:
        log.exception("mc_ctl command failed")
        embed = discord.Embed(
            title="💥 Communication failure",
            description="Could not reach Crafty controller.",
            color=discord.Color.red(),
        )
        await interaction.followup.send(embed=embed)


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
    if not DISCORD_TOKEN or not CRAFTY_URL or not CRAFTY_TOKEN:
        raise SystemExit("Missing required environment variables.")

    bot.run(DISCORD_TOKEN)
