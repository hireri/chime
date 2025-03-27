import discord
from discord.ext import commands
import datetime
import platform
import psutil
import os, sys
from config import config
from core.basecog import BaseCog


class Debug(BaseCog):
    """debug commands OWNER ONLY"""

    @commands.command(name="reload_config", brief="reload the bot configuration")
    @commands.is_owner()
    async def reload_config(self, ctx):
        """reload the bot configuration from the config file"""
        if config.reload():
            embed = self.success_embed(
                description="the configuration has been successfully reloaded.",
            )
        else:
            embed = self.warning_embed(
                description="the configuration file hasn't been modified since last reload.",
            )

        await ctx.reply(embed=embed)

    @commands.command(name="dbg", brief="debug the bot configuration")
    @commands.is_owner()
    async def debug_config(self, ctx):
        """owner-only command to display all configuration variables with examples"""
        config.reload()

        category_pages = {}

        overview_pages = []
        overview_embed = self.embed(title="config debug: overview")
        overview_embed.set_thumbnail(url=None)

        overview_embed.add_field(
            name="quick stats",
            value=(
                f"Bot: `{self.bot.user}`\n"
                f"Prefix: `{config.PREFIX}`\n"
                f"Servers: `{len(self.bot.guilds)}`\n"
                f"Commands: `{len(list(self.bot.commands))}`\n"
                f"Cogs: `{len(self.bot.cogs)}`\n"
                f"Last config reload: <t:{int(datetime.datetime.utcnow().timestamp())}:R>"
            ),
        )

        overview_pages.append(overview_embed)
        category_pages["overview"] = overview_pages

        colors_pages = []

        color_overview = self.embed(title="config debug: colors overview")
        color_overview.set_thumbnail(url=None)

        for color_name, color_value in config.COLORS.items():
            hex_color = f"{color_value:06x}"
            color_url = f"https://singlecolorimage.com/get/{hex_color}/32x32"

            color_overview.add_field(
                name=f"{color_name}",
                value=(
                    f"Hex: `{hex(color_value)}`\n"
                    f"Int: `{color_value}`\n"
                    f"[■]({color_url})"
                ),
                inline=True,
            )

        colors_pages.append(color_overview)

        for color_name, color_value in config.COLORS.items():
            color_embed = discord.Embed(
                title=f"color: {color_name}",
                description=f"this is how {color_name} looks as an embed color",
                color=color_value,
            )
            hex_color = f"{color_value:06x}"
            color_embed.set_thumbnail(
                url=f"https://singlecolorimage.com/get/{hex_color}/32x32"
            )

            color_embed.add_field(
                name="color details",
                value=(
                    f"Name: `{color_name}`\n"
                    f"Hex: `{hex(color_value)}`\n"
                    f"Int: `{color_value}`\n"
                    f"RGB: `{int(hex_color[0:2], 16)}, {int(hex_color[2:4], 16)}, {int(hex_color[4:6], 16)}`"
                ),
                inline=False,
            )

            color_embed.add_field(
                name="usage example",
                value=(
                    f"```python\n"
                    f"# In commands\n"
                    f"embed = discord.Embed(color={color_name}_COLOR)\n\n"
                    f"# From config\n"
                    f"embed = discord.Embed(color=config.COLORS['{color_name}'])\n"
                    f"```"
                ),
                inline=False,
            )

            colors_pages.append(color_embed)

        category_pages["colors"] = colors_pages

        icons_pages = []

        icons_embed = self.embed(title="config debug: icons")
        icons_embed.set_thumbnail(url=None)

        for icon_name, icon_value in config.ICONS.items():
            icons_embed.add_field(
                name=f"{icon_name}",
                value=(
                    f"Icon: {icon_value}\n"
                    f"In text: {icon_value} example text\n"
                    f"Usage: `{icon_name}_ICON`"
                ),
                inline=True,
            )

        icons_pages.append(icons_embed)
        category_pages["icons"] = icons_pages

        system_pages = []

        system_embed = self.embed(title="config debug: system info")
        system_embed.set_thumbnail(url=None)

        system_embed.add_field(
            name="versions",
            value=(
                f"Python: `{platform.python_version()}`\n"
                f"discord.py: `{discord.__version__}`\n"
                f"OS: `{platform.system()} {platform.release()}`"
            ),
            inline=True,
        )

        uptime = datetime.datetime.utcnow() - self.bot.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        uptime_str = f"`{days}d {hours}h {minutes}m {seconds}s`"

        process = psutil.Process()
        system_embed.add_field(
            name="resources",
            value=(
                f"Process ID: `{os.getpid()}`\n"
                f"Memory usage: `{process.memory_info().rss / 1024**2:.2f} MB`\n"
                f"CPU usage: `{psutil.cpu_percent()}%`\n"
                f"Threads: `{process.num_threads()}`\n"
                f"Uptime: {uptime_str}"
            ),
            inline=True,
        )

        system_pages.append(system_embed)

        python_embed = self.embed(title="config debug: python details")
        python_embed.set_thumbnail(url=None)

        python_embed.add_field(
            name="python environment",
            value=(
                f"Version: `{platform.python_version()}`\n"
                f"Implementation: `{platform.python_implementation()}`\n"
                f"Compiler: `{platform.python_compiler()}`\n"
                f"Build: `{platform.python_build()[1]}`\n"
                f"Path: `{sys.executable}`"
            ),
            inline=False,
        )

        paths = "\n".join([f"`{p}`" for p in sys.path[:5]])
        if len(sys.path) > 5:
            paths += f"\n... and {len(sys.path) - 5} more paths"

        python_embed.add_field(name="module paths", value=paths, inline=False)

        system_pages.append(python_embed)

        sys_details_embed = self.embed(title="config debug: detailed system info")
        sys_details_embed.set_thumbnail(url=None)

        virtual_memory = psutil.virtual_memory()
        disk_usage = psutil.disk_usage("/")

        sys_details_embed.add_field(
            name="memory",
            value=(
                f"Total: `{virtual_memory.total / (1024**3):.2f} GB`\n"
                f"Available: `{virtual_memory.available / (1024**3):.2f} GB`\n"
                f"Used: `{virtual_memory.used / (1024**3):.2f} GB`\n"
                f"Percent: `{virtual_memory.percent}%`"
            ),
            inline=True,
        )

        sys_details_embed.add_field(
            name="disk",
            value=(
                f"Total: `{disk_usage.total / (1024**3):.2f} GB`\n"
                f"Free: `{disk_usage.free / (1024**3):.2f} GB`\n"
                f"Used: `{disk_usage.used / (1024**3):.2f} GB`\n"
                f"Percent: `{disk_usage.percent}%`"
            ),
            inline=True,
        )

        cpu_info = f"Cores: `{psutil.cpu_count(logical=False)}`\n"
        cpu_info += f"Logical CPUs: `{psutil.cpu_count()}`\n"
        cpu_info += f"Current usage: `{psutil.cpu_percent()}%`\n"

        try:
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                cpu_info += f"Frequency: `{cpu_freq.current:.2f} MHz`"
        except:
            pass

        sys_details_embed.add_field(name="cpu", value=cpu_info, inline=True)

        system_pages.append(sys_details_embed)
        category_pages["system"] = system_pages

        bot_pages = []

        bot_embed = self.embed(title="config debug: bot info")
        bot_embed.set_thumbnail(url=None)

        bot_embed.add_field(
            name="identity",
            value=(
                f"Name: `{self.bot.user.name}`\n"
                f"ID: `{self.bot.user.id}`\n"
                f"Created: <t:{int(self.bot.user.created_at.timestamp())}:F>\n"
                f"Verified: `{self.bot.user.verified}`\n"
                f"Public: `{self.bot.user.public_flags.system}`"
            ),
            inline=True,
        )

        guild_count = len(self.bot.guilds)
        member_count = sum(g.member_count for g in self.bot.guilds)
        user_count = len(self.bot.users)

        bot_embed.add_field(
            name="statistics",
            value=(
                f"Guilds: `{guild_count}`\n"
                f"Members (total): `{member_count}`\n"
                f"Cached users: `{user_count}`\n"
                f"Commands: `{len(list(self.bot.commands))}`\n"
                f"Cogs: `{len(self.bot.cogs)}`"
            ),
            inline=True,
        )

        bot_pages.append(bot_embed)

        commands_embed = self.embed(title="config debug: commands and cogs")
        commands_embed.set_thumbnail(url=None)

        cogs_text = ""
        for cog_name, cog in self.bot.cogs.items():
            cog_commands = len(cog.get_commands())
            cogs_text += f"`{cog_name}`: {cog_commands} commands\n"

        commands_embed.add_field(
            name=f"cogs ({len(self.bot.cogs)})",
            value=cogs_text or "No cogs loaded",
            inline=True,
        )

        total_commands = len(list(self.bot.commands))
        hidden_commands = len([c for c in self.bot.commands if c.hidden])
        owner_commands = len(
            [
                c
                for c in self.bot.commands
                if c.checks and any("is_owner" in str(check) for check in c.checks)
            ]
        )

        commands_embed.add_field(
            name=f"commands ({total_commands})",
            value=(
                f"Total: `{total_commands}`\n"
                f"Hidden: `{hidden_commands}`\n"
                f"Owner-only: `{owner_commands}`"
            ),
            inline=True,
        )

        bot_pages.append(commands_embed)

        perf_embed = self.embed(title="config debug: performance")
        perf_embed.set_thumbnail(url=None)

        perf_embed.add_field(
            name="connection",
            value=(
                f"Websocket latency: `{round(self.bot.latency * 1000)}ms`\n"
                f"Shard count: `{self.bot.shard_count or 1}`"
            ),
            inline=True,
        )

        uptime = datetime.datetime.utcnow() - self.bot.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)

        perf_embed.add_field(
            name="uptime",
            value=(
                f"Started: <t:{int(self.bot.start_time.timestamp())}:F>\n"
                f"Uptime: `{days}d {hours}h {minutes}m {seconds}s`"
            ),
            inline=True,
        )

        bot_pages.append(perf_embed)
        category_pages["bot"] = bot_pages

        config_pages = []

        config_embed = self.embed(title="config debug: configuration")
        config_embed.set_thumbnail(url=None)

        last_modified_timestamp = int(config._last_modified)
        current_timestamp = int(datetime.datetime.utcnow().timestamp())

        config_embed.add_field(
            name="file info",
            value=(
                f"Path: `{config.config_path}`\n"
                f"Size: `{os.path.getsize(config.config_path)} bytes`\n"
                f"Last modified: <t:{last_modified_timestamp}:F>\n"
                f"Last reload: <t:{current_timestamp}:R>"
            ),
            inline=True,
        )

        config_embed.add_field(
            name="prefix",
            value=(
                f"Current: `{config.PREFIX}`\n" f"Usage example: `{config.PREFIX}help`"
            ),
            inline=True,
        )

        config_pages.append(config_embed)

        content_embed = self.embed(title="config debug: file content")
        content_embed.set_thumbnail(url=None)

        with open(config.config_path, "r") as f:
            config_content = f.read()

        content_chunks = []
        if len(config_content) > 1000:
            lines = config_content.split("\n")
            current_chunk = ""

            for line in lines:
                if len(current_chunk) + len(line) + 1 > 1000:
                    content_chunks.append(current_chunk)
                    current_chunk = line + "\n"
                else:
                    current_chunk += line + "\n"

            if current_chunk:
                content_chunks.append(current_chunk)
        else:
            content_chunks = [config_content]

        for i, chunk in enumerate(content_chunks):
            if i == 0:
                content_embed.description = f"```ini\n{chunk}\n```"
                config_pages.append(content_embed)
            else:
                page_embed = self.embed(
                    title=f"config debug: file content (part {i+1})"
                )
                page_embed.set_thumbnail(url=None)
                page_embed.description = f"```ini\n{chunk}\n```"
                config_pages.append(page_embed)

        category_pages["config"] = config_pages

        await self.create_combined_menu(
            ctx, category_pages, placeholder="select a category..."
        )


async def setup(bot):
    await bot.add_cog(Debug(bot))
