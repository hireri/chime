import datetime
import logging
import os

import aiohttp
import discord
from discord.ext import commands

from .database import db
from .prefixes import get_prefix_callable
from .utils import would_invoke

logger = logging.getLogger(__name__)


class Core(commands.AutoShardedBot):
    def __init__(self):
        intents = discord.Intents.all()

        super().__init__(
            command_prefix=get_prefix_callable(),
            intents=intents,
            help_command=None,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False),
        )

        self.start_time = datetime.datetime.utcnow()
        self.session = None
        self.strip_after_prefix = True
        self.application_emojis = {}

    async def setup_hook(self):
        """Initialize aiohttp session, database, and any other async startup tasks"""
        self.session = aiohttp.ClientSession()

        await db.setup(self)
        logger.info("Database initialized")

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

        if not self.application_emojis:
            emojis = await self.fetch_application_emojis()
            self.application_emojis = {emoji.id: emoji for emoji in emojis}

    async def on_ready(self):
        """Called when the bot is ready and connected to Discord"""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")

    async def on_guild_join(self, guild):
        """Called when the bot joins a new guild"""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")

        await db.update_guild(guild.id, guild.name)

    async def on_message(self, message):
        """insert user before processing commands"""
        if (message.author.bot or not message.guild) or (
            message.author.id in db.cache.entity_keys
        ):
            return

        if await would_invoke(self, message):
            await db.update_user(message.author.id, message.author.name)

        await self.process_commands(message)

    async def fetch_image(self, url):
        """Fetch an image from a URL"""
        async with self.session.get(url) as response:
            if response.status != 200:
                return None
            return await response.read()

    async def close(self):
        """Clean up resources when the bot is shutting down"""
        if self.session:
            await self.session.close()

        await db.close()

        await super().close()
