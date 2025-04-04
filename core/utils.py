import discord
from discord.ext import commands

from .prefixes import prefix_manager


async def would_invoke_command(
    bot: commands.Bot, message: discord.Message, command_name: str = None
) -> bool:
    prefixes = await prefix_manager.get_prefix(bot, message)
    if not isinstance(prefixes, (list, tuple)):
        prefixes = [prefixes]

    for prefix in prefixes:
        if message.content.startswith(prefix):
            potential_command_name = (
                (message.content[len(prefix) :].split(" ", 1)[0]).lower().strip()
            )

            if command_name:
                if potential_command_name == command_name and bot.get_command(
                    command_name
                ):
                    return True
            elif bot.get_command(potential_command_name):
                return True

    return False
