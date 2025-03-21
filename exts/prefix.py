import discord
from discord.ext import commands
import logging
import config
from core.basecog import BaseCog
from core.prefixes import prefix_manager
from core.database import db
from typing import Optional

logger = logging.getLogger(__name__)


class PrefixCommands(BaseCog):
    """Commands for managing bot prefixes"""

    @commands.group(
        name="prefix", invoke_without_command=True, brief="Manage bot prefixes"
    )
    async def prefix(self, ctx):
        """Base command for managing bot prefixes

        Without subcommands, shows information about the current prefix
        """
        embed = self.embed(title="prefix information")

        current_prefix = config.PREFIX

        user_prefix = await prefix_manager.get_user_prefix(ctx.author.id)
        if user_prefix:
            embed.add_field(
                name="your personal prefix",
                value=f"`{user_prefix}` (active)",
                inline=True,
            )
            current_prefix = user_prefix

        if ctx.guild:
            guild_prefix = await prefix_manager.get_guild_prefix(ctx.guild.id)
            if guild_prefix:
                status = "(inactive)" if user_prefix else "(active)"
                embed.add_field(
                    name="server prefix",
                    value=f"`{guild_prefix}` {status}",
                    inline=True,
                )
                if not user_prefix:
                    current_prefix = guild_prefix

        # Add default prefix info - only if active
        if not user_prefix and not (
            ctx.guild and await prefix_manager.get_guild_prefix(ctx.guild.id)
        ):
            embed.add_field(
                name="default prefix", value=f"`{config.PREFIX}` (active)", inline=True
            )

        # Add usage examples
        examples = [
            f"`{current_prefix}prefix set <p>` - Set server prefix to <p>",
            f"`{current_prefix}prefix self <p>` - Set your personal prefix to <p>",
            f"`{current_prefix}prefix view` - View current prefix info",
            f"`{current_prefix}prefix remove` - Remove custom server prefix",
            f"`{current_prefix}prefix self reset` - Remove your personal prefix",
        ]

        embed.add_field(name="examples", value="\n".join(examples), inline=False)

        # Add note about mentions
        embed.set_footer(
            text="you can always @me as a prefix, regardless of custom settings."
        )

        await ctx.send(embed=embed)

    @prefix.command(name="set", brief="Set server prefix")
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def prefix_set(self, ctx, new_prefix: str):
        """Set a custom prefix for the current server

        Args:
            new_prefix: The new prefix to use

        Requires:
            manage_guild permission
        """
        if len(new_prefix) > 10:
            return await ctx.send(
                embed=self.error_embed(
                    description="prefix must be 10 characters or less"
                )
            )

        # Update guild in database if needed
        await db.update_guild(ctx.guild.id, ctx.guild.name)

        # Set the new prefix
        await prefix_manager.set_guild_prefix(ctx.guild.id, new_prefix)

        await ctx.send(
            embed=self.success_embed(description=f"server prefix set to `{new_prefix}`")
        )

    @prefix.command(name="view", brief="View current prefix")
    async def prefix_view(self, ctx):
        """View the current prefix settings

        Shows default, server, and personal prefixes
        """
        # Use the same logic as the base prefix command
        await self.prefix(ctx)

    @prefix.command(name="self", brief="Set your personal prefix")
    async def prefix_self(self, ctx, new_prefix: Optional[str] = None):
        """Set or remove your personal prefix

        Args:
            new_prefix: The new prefix to use, or "reset" to remove
                       If not provided, shows your current prefix
        """
        # If no prefix is provided, show current prefix
        if new_prefix is None:
            user_prefix = await prefix_manager.get_user_prefix(ctx.author.id)

            if user_prefix:
                await ctx.send(
                    embed=self.embed(
                        description=f"your personal prefix is `{user_prefix}`"
                    )
                )
            else:
                await ctx.send(
                    embed=self.embed(description="you don't have a personal prefix set")
                )
            return

        # If prefix is 'reset', remove personal prefix
        if new_prefix.lower() == "reset":
            result = await prefix_manager.remove_user_prefix(ctx.author.id)

            if result:
                await ctx.send(
                    embed=self.success_embed(
                        description="your personal prefix has been reset"
                    )
                )
            else:
                await ctx.send(
                    embed=self.warning_embed(
                        description="you don't have a personal prefix to reset"
                    )
                )
            return

        # Check prefix length
        if len(new_prefix) > 10:
            return await ctx.send(
                embed=self.error_embed(
                    description="prefix must be 10 characters or less"
                )
            )

        # Update user in database if needed
        await db.update_user(ctx.author.id, ctx.author.name, ctx.author.discriminator)

        # Set the new prefix
        await prefix_manager.set_user_prefix(ctx.author.id, new_prefix)

        await ctx.send(
            embed=self.success_embed(
                description=f"your personal prefix set to `{new_prefix}`"
            )
        )

    @prefix.command(name="remove", brief="Remove server prefix")
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def prefix_remove(self, ctx):
        """Remove the custom prefix for the current server

        Requires:
            manage_guild permission
        """
        result = await prefix_manager.remove_guild_prefix(ctx.guild.id)

        if result:
            await ctx.send(
                embed=self.success_embed(
                    description=f"server prefix removed, using `{config.PREFIX}` now"
                )
            )
        else:
            await ctx.send(
                embed=self.warning_embed(
                    description="this server doesn't have a custom prefix set"
                )
            )


async def setup(bot):
    # Ensure database is ready and attached to bot
    await db.setup(bot)
    await bot.add_cog(PrefixCommands(bot))
