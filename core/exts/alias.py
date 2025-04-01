import logging

from discord.ext import commands

from core.basecog import BaseCog
from core.database import db

logger = logging.getLogger(__name__)


class Alias(BaseCog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logger

    def is_valid_command(self, command_name: str) -> bool:
        command = self.bot.get_command(command_name)
        return command is not None

    @commands.group(name="alias", description="manage command aliases")
    async def alias(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self.list_aliases)

    @alias.command(name="view", description="view command execution for alias")
    async def alias_view(self, ctx, alias):
        command_parts = await db.get_alias(ctx.guild.id, alias)

        if command_parts is None:
            return await ctx.send(
                embed=self.warning_embed(
                    description=f"alias **{alias}** does not exist"
                )
            )

        command = " ".join(command_parts)
        await ctx.send(
            embed=self.embed(
                description=f"command execution for **{alias}**: **{ctx.prefix}{command}**"
            )
        )

    @alias.command(name="add", description="create an alias for a command")
    @commands.has_permissions(manage_guild=True)
    async def add_alias(self, ctx: commands.Context, alias: str, *, command: str):
        if self.is_valid_command(alias):
            return await ctx.send(
                embed=self.error_embed(
                    description=f"the alias **{alias}** conflicts with a command"
                )
            )

        elif not self.is_valid_command(command):
            return await ctx.send(
                embed=self.error_embed(
                    description=f"the command **{command}** does not exist"
                )
            )

        insert, is_new = await db.add_alias(ctx.guild.id, alias, command)

        if not is_new:
            return await ctx.send(
                embed=self.warning_embed(
                    f"this alias is taken for **{' '.join(insert['command'])}**"
                )
            )

        await ctx.send(
            embed=self.success_embed(
                description=f"alias **{alias}** created for command **{command}**"
            )
        )

    @alias.command(name="list", description="list all aliases for this server")
    async def list_aliases(self, ctx: commands.Context):
        aliases = await db.get_aliases(ctx.guild.id)
        if not aliases:
            return await ctx.send(
                embed=self.warning_embed(description="no aliases set for this server")
            )

        print(aliases)
        aliases_per_page = 10
        pages = []
        for i in range(0, len(aliases), aliases_per_page):
            page = aliases[i : i + aliases_per_page]
            pages.append(
                self.embed(
                    description="\n".join(
                        f"- **{alias['alias']}**: **{' '.join(alias['command'])}**"
                        for alias in page
                    )
                ).set_author(
                    name=f"{ctx.guild.name}'s aliases", icon_url=ctx.guild.icon.url
                )
            )

        await self.paginate(ctx, pages)

    @alias.command(name="remove", description="remove an alias")
    @commands.has_permissions(manage_guild=True)
    async def remove_alias(self, ctx: commands.Context, alias: str):
        was_removed, command = await db.remove_alias(ctx.guild.id, alias)

        if not was_removed:
            return await ctx.send(
                embed=self.warning_embed(
                    description=f"alias **{alias}** does not exist"
                )
            )

        await ctx.send(
            embed=self.success_embed(description=f"alias **{alias}** removed")
        )

    @alias.command(name="removeall", description="remove all aliases for a command")
    @commands.has_permissions(manage_guild=True)
    async def remove_all_aliases(self, ctx: commands.Context, *, command: str):
        command_parts = command.split(" ")

        count = await db.remove_aliases_cmd(ctx.guild.id, command_parts)

        if count > 0:
            await ctx.send(
                embed=self.success_embed(
                    description=f"all aliases for command **{command}** removed ({count} aliases)"
                )
            )
        else:
            await ctx.send(
                embed=self.warning_embed(
                    description=f"no aliases found for command **{command}**"
                )
            )

    @alias.command(name="reset", description="remove all aliases for this server")
    @commands.has_permissions(manage_guild=True)
    async def reset_aliases(self, ctx: commands.Context):
        count = await db.reset_aliases(ctx.guild.id)

        await ctx.send(
            embed=self.success_embed(
                description=f"server's aliases reset ({count} aliases)"
            )
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Alias(bot))
