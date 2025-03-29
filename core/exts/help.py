from typing import TYPE_CHECKING
import logging
import discord
from discord.ext import commands
import config

logger = logging.getLogger(__name__)


class MyHelpCommand(commands.HelpCommand):
    def __init__(self):
        super().__init__(
            command_attrs={
                "aliases": ["h", "commands"],
                "brief": "shows help information",
            }
        )

    def get_command_signature(self, command):
        return (
            f"{self.context.clean_prefix}{command.qualified_name} {command.signature}"
        )

    def format_command_tree(self, command, level=0):
        tree = f"{'  ' * level}{command.name}\n"
        if isinstance(command, commands.Group):
            for subcommand in command.commands:
                tree += self.format_command_tree(subcommand, level + 1)
        return tree

    def get_command_description(self, command):
        return command.short_doc or command.description or "no description"

    async def send_bot_help(self, mapping):
        config.config.reload()

        embeds = []
        for cog, cog_commands in mapping.items():
            if cog is None or not await self.filter_commands(cog_commands):
                continue
            embed = discord.Embed(
                title=(
                    f"help - {cog.qualified_name}" if cog else "uncategorized commands"
                ),
                color=config.MAIN_COLOR,
            )
            for command in await self.filter_commands(cog_commands):
                embed.add_field(
                    name=self.get_command_signature(command),
                    value=self.get_command_description(command),
                    inline=True,
                )
            embeds.append(embed)

        options = [
            discord.SelectOption(label=embed.title, value=str(i))
            for i, embed in enumerate(embeds)
        ]
        select = discord.ui.Select(placeholder="choose a category...", options=options)

        async def select_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(embed=embeds[int(select.values[0])])

        select.callback = select_callback
        view = discord.ui.View().add_item(select)
        home_embed = discord.Embed(
            title="command list",
            description=f"""welcome to #stinkcord 💗
- {config.LINK_ICON} [support](https://discord.gg/chime)
- {config.LINK_ICON} [command list](https://google.com)
-# navigate through categories using the dropdown""",
            color=config.MAIN_COLOR,
        )
        home_embed.set_author(
            name=self.context.bot.user.name, icon_url=self.context.bot.user.avatar.url
        )
        home_embed.set_footer(
            text=f"{len(self.context.bot.commands)} commands, .help <cmd> for command help"
        )
        await self.get_destination().send(embed=home_embed, view=view)

    async def send_cog_help(self, cog):
        config.config.reload()

        embed = discord.Embed(
            title=f"help - {cog.qualified_name}",
            color=config.MAIN_COLOR,
        )
        for command in await self.filter_commands(cog.get_commands()):
            embed.add_field(
                name=self.get_command_signature(command),
                value=self.get_command_description(command),
                inline=True,
            )
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command):
        config.config.reload()

        embed = discord.Embed(
            title=f"help - {command.qualified_name}",
            description=self.get_command_description(command),
            color=config.MAIN_COLOR,
        )
        embed.add_field(
            name="usage",
            value=f"```\n{self.get_command_signature(command)}```",
            inline=True,
        )
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        config.config.reload()

        embed = discord.Embed(
            title=f"help - {group.qualified_name}",
            description=self.get_command_description(group),
            color=config.MAIN_COLOR,
        )
        embed.add_field(
            name="usage",
            value=f"```\n{self.get_command_signature(group)}```",
            inline=True,
        )

        subcommands = list(group.commands)
        subcommand_list = "\n".join(
            [
                f"`{subcmd.name}`: {self.get_command_description(subcmd)}"
                for subcmd in subcommands
            ]
        )
        embed.add_field(name="subcommands", value=subcommand_list, inline=True)

        options = [
            discord.SelectOption(label=subcommand.name, value=subcommand.name)
            for subcommand in subcommands
        ]
        select = discord.ui.Select(
            placeholder="choose a subcommand...", options=options
        )

        async def select_callback(interaction: discord.Interaction):
            try:
                subcommand = group.get_command(select.values[0])
                view = discord.ui.View().add_item(select)
                await interaction.response.edit_message(view=view)
                await interaction.followup.send(
                    embed=await self.create_subcommand_embed(subcommand), ephemeral=True
                )
            except Exception as e:
                print(e)

        select.callback = select_callback
        view = discord.ui.View().add_item(select)
        await self.get_destination().send(embed=embed, view=view)

    async def create_subcommand_embed(self, command):
        config.config.reload()

        embed = discord.Embed(
            title=f"help - {command.qualified_name}",
            description=self.get_command_description(command)
            or command.description
            or "no detailed help available.",
            color=config.MAIN_COLOR,
        )
        embed.add_field(
            name="usage",
            value=f"```\n{self.get_command_signature(command)}```",
            inline=True,
        )
        return embed

    async def command_not_found(self, string):
        return f"no command called '{string}' found."

    async def send_error_message(self, error):
        config.config.reload()

        embed = discord.Embed(
            description=f"{config.ERROR_ICON} {error}",
            color=config.ERROR_COLOR,
        )
        await self.get_destination().send(embed=embed)


async def setup(bot):
    bot.help_command = MyHelpCommand()
