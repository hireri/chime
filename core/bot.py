import discord
from discord.ext import commands
import logging
import datetime
import aiohttp
import traceback
import sys
import os
import config
from config import PREFIX

logger = logging.getLogger(__name__)


class Core(commands.Bot):
    def __init__(self):
        # Initialize with all intents for maximum versatility
        intents = discord.Intents.all()

        # Initialize the bot with prefix commands
        super().__init__(
            command_prefix=commands.when_mentioned_or(PREFIX),
            intents=intents,
            help_command=None,
        )

        # Bot variables
        self.start_time = datetime.datetime.utcnow()
        self.session = None

    async def setup_hook(self):
        """Initialize aiohttp session and any other async startup tasks"""
        self.session = aiohttp.ClientSession()

        # Load all extensions from the exts directory
        loaded_extensions = []
        failed_extensions = []

        await self.load_extension("jishaku")
        for filename in os.listdir("./core/exts"):
            if filename.endswith(".py"):
                extension = f"core.exts.{filename[:-3]}"
                try:
                    await self.load_extension(extension)
                    loaded_extensions.append(extension)
                    logger.info(f"Loaded extension: {extension}")
                except Exception as e:
                    failed_extensions.append(extension)
                    logger.error(f"Failed to load extension {extension}: {e}")

        for filename in os.listdir("./exts"):
            if filename.endswith(".py"):
                extension = f"exts.{filename[:-3]}"
                try:
                    await self.load_extension(extension)
                    loaded_extensions.append(extension)
                    logger.info(f"Loaded extension: {extension}")
                except Exception as e:
                    failed_extensions.append(extension)
                    logger.error(f"Failed to load extension {extension}: {e}")

        logger.info(f"Loaded {len(loaded_extensions)} extensions")
        if failed_extensions:
            logger.warning(f"Failed to load {len(failed_extensions)} extensions")

        logger.info("Bot setup complete")

    async def on_ready(self):
        """Called when the bot is ready and connected to Discord"""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")

    async def on_guild_join(self, guild):
        """Called when the bot joins a new guild"""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")

    async def close(self):
        """Clean up resources when the bot is shutting down"""
        if self.session:
            await self.session.close()
        await super().close()
