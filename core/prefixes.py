import discord
from discord.ext import commands
import asyncio
import logging
import config
from typing import List, Union, Optional, Dict, Callable
from .database import db

logger = logging.getLogger(__name__)


class PrefixManager:
    """Manages custom prefixes for guilds and users"""

    def __init__(self, default_prefix: str = None):
        """Initialize the prefix manager

        Args:
            default_prefix (str, optional): The default prefix to fall back to
        """
        self.default_prefix = default_prefix or config.PREFIX

        # Cache to reduce database calls
        self._guild_cache: Dict[int, str] = {}
        self._user_cache: Dict[int, str] = {}

        # Metrics for monitoring
        self.cache_hits = 0
        self.cache_misses = 0

        # Set maximum cache size
        self.max_cache_size = 1000

    async def get_prefix(
        self, bot: commands.Bot, message: discord.Message
    ) -> List[str]:
        """Determine the appropriate command prefix based on the message context

        This is the function that gets passed to the bot's command_prefix parameter.
        It determines the prefix in the following priority order:
        1. User-specific prefix (if set)
        2. Guild-specific prefix (if in a guild and set)
        3. Default prefix (only if no custom prefixes are set)

        Args:
            bot (commands.Bot): The bot instance
            message (discord.Message): The message context

        Returns:
            List[str]: A list of valid prefixes for the message
        """
        prefixes = []

        # Always accept mentions as prefix
        prefixes.extend([f"<@{bot.user.id}> ", f"<@!{bot.user.id}> "])

        # Check for user-specific prefix (highest priority)
        user_prefix = await self.get_user_prefix(message.author.id)
        if user_prefix:
            prefixes.append(user_prefix)
            return prefixes  # User prefix overrides all others

        # If in a guild, check for guild-specific prefix
        if message.guild:
            guild_prefix = await self.get_guild_prefix(message.guild.id)
            if guild_prefix:
                prefixes.append(guild_prefix)
                return prefixes  # Guild prefix overrides default

        # Only use default prefix if no custom prefixes are set
        prefixes.append(self.default_prefix)

        return prefixes

    async def get_guild_prefix(self, guild_id: int) -> Optional[str]:
        """Get the custom prefix for a guild

        Args:
            guild_id (int): The guild ID

        Returns:
            Optional[str]: The custom prefix, or None if not set
        """
        # Check cache first
        if guild_id in self._guild_cache:
            self.cache_hits += 1
            return self._guild_cache[guild_id]

        # Not in cache, query the database
        self.cache_misses += 1
        prefix = await db.get_prefix("guild", guild_id)

        # Update cache
        if prefix:
            self._add_to_cache(self._guild_cache, guild_id, prefix)

        return prefix

    async def get_user_prefix(self, user_id: int) -> Optional[str]:
        """Get the custom prefix for a user

        Args:
            user_id (int): The user ID

        Returns:
            Optional[str]: The custom prefix, or None if not set
        """
        # Check cache first
        if user_id in self._user_cache:
            self.cache_hits += 1
            return self._user_cache[user_id]

        # Not in cache, query the database
        self.cache_misses += 1
        prefix = await db.get_prefix("user", user_id)

        # Update cache
        if prefix:
            self._add_to_cache(self._user_cache, user_id, prefix)

        return prefix

    def _add_to_cache(self, cache: Dict[int, str], key: int, value: str) -> None:
        """Add an item to the cache, maintaining maximum cache size

        Args:
            cache (Dict[int, str]): The cache dictionary
            key (int): The key to add
            value (str): The value to add
        """
        # If cache is full, remove oldest item (first added)
        if len(cache) >= self.max_cache_size:
            oldest_key = next(iter(cache))
            del cache[oldest_key]

        # Add new item
        cache[key] = value

    async def set_guild_prefix(self, guild_id: int, prefix: str) -> None:
        """Set a custom prefix for a guild

        Args:
            guild_id (int): The guild ID
            prefix (str): The new prefix
        """
        await db.set_prefix("guild", guild_id, prefix)

        # Update cache
        self._guild_cache[guild_id] = prefix

    async def set_user_prefix(self, user_id: int, prefix: str) -> None:
        """Set a custom prefix for a user

        Args:
            user_id (int): The user ID
            prefix (str): The new prefix
        """
        await db.set_prefix("user", user_id, prefix)

        # Update cache
        self._user_cache[user_id] = prefix

    async def remove_guild_prefix(self, guild_id: int) -> bool:
        """Remove the custom prefix for a guild

        Args:
            guild_id (int): The guild ID

        Returns:
            bool: True if a prefix was removed, False otherwise
        """
        result = await db.remove_prefix("guild", guild_id)

        # Update cache
        if result and guild_id in self._guild_cache:
            del self._guild_cache[guild_id]

        return result

    async def remove_user_prefix(self, user_id: int) -> bool:
        """Remove the custom prefix for a user

        Args:
            user_id (int): The user ID

        Returns:
            bool: True if a prefix was removed, False otherwise
        """
        result = await db.remove_prefix("user", user_id)

        # Update cache
        if result and user_id in self._user_cache:
            del self._user_cache[user_id]

        return result

    def clear_cache(self) -> None:
        """Clear the prefix cache"""
        self._guild_cache.clear()
        self._user_cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get prefix cache statistics

        Returns:
            Dict[str, int]: Cache statistics
        """
        return {
            "hits": self.cache_hits,
            "misses": self.cache_misses,
            "guild_cache_size": len(self._guild_cache),
            "user_cache_size": len(self._user_cache),
            "total_cache_size": len(self._guild_cache) + len(self._user_cache),
            "max_cache_size": self.max_cache_size,
        }


# Create a global instance of the prefix manager
prefix_manager = PrefixManager()


# Function to get as callable for bot initialization
def get_prefix_callable() -> Callable:
    """Get the prefix manager's get_prefix method as a callable

    Returns:
        Callable: The prefix resolver function
    """
    return prefix_manager.get_prefix
