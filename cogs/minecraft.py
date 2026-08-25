import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from config import settings
from crafty_api import CraftyClient
from server_registry import ServerDiff, ServerRegistry

log = logging.getLogger("crafty-discord-bot.minecraft")


class MinecraftControlView(discord.ui.View):
    def __init__(self, cog: "Minecraft", server_id: str, server_name: str):
        super().__init__(timeout=60)
        self.cog = cog
        self.server_id = server_id
        self.server_name = server_name

    async def _handle_action(
        self, interaction: discord.Interaction, action: str, verb: str, emoji: str
    ):
        if not await self.cog.validate_context(interaction, restricted=True):
            return

        await interaction.response.defer(thinking=True)
        success = await self.cog.crafty.run_action(self.server_id, action)

        if success:
            embed = discord.Embed(
                title=f"{emoji} {verb} sent",
                description=f"Command sent to **{self.server_name}**.",
                color=discord.Color.blurple(),
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(
                embed=discord.Embed(title="⚠️ Crafty API error", color=discord.Color.orange())
            )

    @discord.ui.button(label="Start", style=discord.ButtonStyle.green, emoji="🟢")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_action(interaction, "start_server", "Start", "🟢")

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.red, emoji="🛑")
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_action(interaction, "stop_server", "Stop", "🛑")

    @discord.ui.button(label="Restart", style=discord.ButtonStyle.blurple, emoji="🔁")
    async def restart_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle_action(interaction, "restart_server", "Restart", "🔁")


class Minecraft(commands.Cog):
    def __init__(self, bot: commands.Bot, crafty: CraftyClient, registry: ServerRegistry):
        self.bot = bot
        self.crafty = crafty
        self.registry = registry
        self.refresh_servers.change_interval(minutes=settings.refresh_interval_minutes)

    async def cog_load(self):
        # The periodic loop; its first tick diffs against the cache already populated
        # by the startup refresh, so nothing is announced as "new" on boot.
        self.refresh_servers.start()

    async def cog_unload(self):
        self.refresh_servers.cancel()

    @property
    def server_keys(self) -> dict[str, dict[str, str]]:
        """Current server cache, keyed by Crafty UUID."""
        return self.registry.servers

    @tasks.loop(minutes=5)
    async def refresh_servers(self):
        diff = await self.registry.refresh()
        if diff.has_changes:
            await self._announce_changes(diff)

    @refresh_servers.before_loop
    async def _before_refresh(self):
        await self.bot.wait_until_ready()

    async def _announce_changes(self, diff: ServerDiff):
        if not settings.allowed_channel_id:
            log.info(
                "Server changes detected (+%d/-%d) but ALLOWED_CHANNEL_ID is unset; skipping",
                len(diff.added),
                len(diff.removed),
            )
            return

        channel = self.bot.get_channel(settings.allowed_channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(settings.allowed_channel_id)
            except Exception:
                log.exception("Could not fetch ALLOWED_CHANNEL_ID for announcements")
                return

        for entry in diff.added:
            try:
                await channel.send(
                    embed=discord.Embed(
                        title="🆕 New server detected",
                        description=f"**{entry['name']}** is now available in `/mc`.",
                        color=discord.Color.green(),
                    )
                )
            except Exception:
                log.exception("Failed to announce new server %s", entry.get("name"))

        for entry in diff.removed:
            try:
                await channel.send(
                    embed=discord.Embed(
                        title="➖ Server removed",
                        description=f"**{entry['name']}** is no longer in Crafty.",
                        color=discord.Color.dark_grey(),
                    )
                )
            except Exception:
                log.exception("Failed to announce removed server %s", entry.get("name"))

    async def is_mod(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == settings.owner_id:
            return True
        if not interaction.guild:
            return False
        member = interaction.user
        if not isinstance(member, discord.Member):
            member = interaction.guild.get_member(interaction.user.id)
        if not member:
            return False
        if settings.mod_role_id:
            return any(role.id == settings.mod_role_id for role in member.roles)
        return False

    async def validate_context(self, interaction: discord.Interaction, restricted: bool = False):
        if settings.allowed_channel_id and interaction.channel.id != settings.allowed_channel_id:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="🚫 Wrong channel",
                    description=f"Use <#{settings.allowed_channel_id}> for this command.",
                    color=discord.Color.red(),
                ),
                ephemeral=True,
            )
            return False

        if restricted and not await self.is_mod(interaction):
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

    async def server_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = []
        for key, entry in self.server_keys.items():
            name = entry.get("name", key)
            if current.lower() in name.lower():
                choices.append(app_commands.Choice(name=name, value=name))
        return choices[:25]

    @app_commands.command(name="mc", description="Query or control Crafty Minecraft servers")
    @app_commands.describe(server="Server name", action="Action to perform")
    @app_commands.choices(
        action=[
            app_commands.Choice(name="📊 Status", value="status"),
            app_commands.Choice(name="🟢 Start", value="start_server"),
            app_commands.Choice(name="🛑 Stop", value="stop_server"),
            app_commands.Choice(name="🔁 Restart", value="restart_server"),
            app_commands.Choice(name="🔧 Update Executable", value="update_executable"),
        ]
    )
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild_id, i.user.id))
    async def mc_manager(
        self,
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
        if not await self.validate_context(interaction, restricted=is_admin_action):
            return

        entry = next(
            (v for v in self.server_keys.values() if v["name"].lower() == server.lower()), None
        )

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
            if action.value == "status":
                data = await self.crafty.get_stats(server_id)
                d = data.get("data", {})
                running = d.get("running", False)
                players_online = d.get("online", 0)
                players_max = d.get("max", 0)

                # Extended stats if available
                cpu = d.get("cpu", "N/A")
                mem = d.get("memory", "N/A")
                ver = d.get("version", "Unknown")

                embed = discord.Embed(
                    title=f"{'🟢' if running else '🔴'} {server_display_name}",
                    description=f"Version: `{ver}`",
                    color=discord.Color.green() if running else discord.Color.red(),
                )
                embed.add_field(
                    name="Status", value=f"**{'ONLINE' if running else 'OFFLINE'}**", inline=True
                )
                embed.add_field(
                    name="Players", value=f"`{players_online}/{players_max}`", inline=True
                )

                if running:
                    embed.add_field(name="CPU Usage", value=f"`{cpu}%`", inline=True)
                    embed.add_field(name="Memory", value=f"`{mem}`", inline=True)

                view = MinecraftControlView(self, server_id, server_display_name)
                await interaction.followup.send(embed=embed, view=view)
            else:
                success = await self.crafty.run_action(server_id, action.value)
                if success:
                    emoji = {
                        "start_server": "🟢",
                        "stop_server": "🛑",
                        "restart_server": "🔁",
                        "update_executable": "🔧",
                    }.get(action.value, "⚙️")
                    verb = {
                        "start_server": "Start",
                        "stop_server": "Stop",
                        "restart_server": "Restart",
                        "update_executable": "Update Executable",
                    }.get(action.value)
                    embed = discord.Embed(
                        title=f"{emoji} {verb} sent",
                        description=f"Command sent to **{server_display_name}**.",
                        color=discord.Color.blurple(),
                    )
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send(
                        embed=discord.Embed(
                            title="⚠️ Crafty API error", color=discord.Color.orange()
                        )
                    )
        except Exception:
            log.exception("mc_ctl command failed")
            await interaction.followup.send(
                embed=discord.Embed(title="💥 Communication failure", color=discord.Color.red())
            )

    @mc_manager.error
    async def mc_manager_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="⌛ Slow down",
                    description=f"Try again in `{error.retry_after:.1f}s`.",
                    color=discord.Color.orange(),
                ),
                ephemeral=True,
            )
        else:
            log.error("Command error: %s", error)


async def setup(bot: commands.Bot):
    # The bot will have the crafty client and registry attached
    await bot.add_cog(Minecraft(bot, bot.crafty, bot.registry))
