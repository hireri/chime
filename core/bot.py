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
from .prefixes import get_prefix_callable
from .database import db

logger = logging.getLogger(__name__)


class Core(commands.Bot):
    def __init__(self):
        # Initialize with all intents for maximum versatility
        intents = discord.Intents.all()

        # Initialize the bot with dynamic prefix function
        super().__init__(
            command_prefix=get_prefix_callable(),
            intents=intents,
            help_command=None,
        )

        # Bot variables
        self.start_time = datetime.datetime.utcnow()
        self.session = None
        self.strip_after_prefix = True

    async def setup_hook(self):
        """Initialize aiohttp session, database, and any other async startup tasks"""
        self.session = aiohttp.ClientSession()

        # Initialize database connection
        await db.setup()
        logger.info("Database initialized")

        # Load all extensions from the exts directory
        loaded_extensions = []
        failed_extensions = []

        # Load jishaku for debugging
        await self.load_extension("jishaku")

        # Load core extensions
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

        # Load user extensions
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

        # Track the guild in database
        await db.update_guild(guild.id, guild.name)

    async def on_message(self, message):
        """Process commands and track user activity"""
        # Don't respond to bots
        if message.author.bot:
            return

        # Update user data in the background
        if not message.author.bot:
            self.loop.create_task(
                db.update_user(
                    message.author.id, message.author.name, message.author.discriminator
                )
            )

        # Process commands
        await self.process_commands(message)

    async def close(self):
        """Clean up resources when the bot is shutting down"""
        if self.session:
            await self.session.close()

        # Close database connection
        await db.close()

        await super().close()
