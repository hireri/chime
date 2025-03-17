import discord
from discord.ext import commands
import datetime
import platform
import psutil
import os, sys
import config
from core.basecog import BaseCog


class Utility(BaseCog):
    """utility commands for the bot"""

    @commands.command(name="ping", brief="check the bot's latency")
    async def ping(self, ctx):
        """check the bot's latency"""
        # Check if config has been modified
        config.config.reload()

        start_time = datetime.datetime.utcnow()

        # send initial response
        message = await ctx.send("pinging...")

        # calculate latency
        end_time = datetime.datetime.utcnow()
        response_time = (end_time - start_time).total_seconds() * 1000
        heartbeat_latency = round(self.bot.latency * 1000)

        # edit the message with the results
        await message.edit(
            content=f"bot latency: {heartbeat_latency}ms\n"
            f"response time: {response_time:.2f}ms"
        )

    @commands.command(name="info", brief="get information about the bot")
    async def info(self, ctx):
        """display information about the bot"""
        # calculate uptime
        uptime = datetime.datetime.utcnow() - self.bot.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        uptime_str = f"`{days}d {hours}h {minutes}m {seconds}s`"

        # get system info
        python_version = platform.python_version()
        discord_version = discord.__version__
        memory_usage = psutil.Process().memory_info().rss / 1024**2  # convert to MB

        # create embed using BaseCog's utility method
        embed = self.embed(
            title="bot information",
            description="a versatile discord bot built with discord.py",
        )

        embed.add_field(name="bot version", value="0.0.1", inline=True)
        embed.add_field(name="python version", value=python_version, inline=True)
        embed.add_field(name="discord.py version", value=discord_version, inline=True)

        embed.add_field(name="uptime", value=uptime_str, inline=True)
        embed.add_field(
            name="memory usage", value=f"{memory_usage:.2f} mb", inline=True
        )
        embed.add_field(name="servers", value=str(len(self.bot.guilds)), inline=True)

        embed.set_footer(text=f"requested by {ctx.author}")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Utility(bot))
