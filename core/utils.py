import discord
from discord.ext import commands

from .prefixes import prefix_manager


async def would_invoke_command(bot: commands.Bot, message: discord.Message) -> bool:
    """Check if a message would invoke a command without actually invoking it

    Args:
        bot: The bot instance
        message: The message to check

    Returns:
        bool: True if the message would invoke a command, False otherwise
    """
    prefixes = await prefix_manager.get_prefix(bot, message)

    for prefix in prefixes:
        if message.content.startswith(prefix):
            command_name = message.content[len(prefix) :].split()[0]

            if bot.get_command(command_name):
                return True

    return False
