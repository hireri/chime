import traceback
from typing import Optional, Union

import discord
from core.database import db
import copy
from discord.ext import commands

import config
from core.basecog import BaseCog


class ErrorHandler(BaseCog):
    """advanced error handling for the bot"""

    async def _send_error_message(
        self,
        ctx: Union[commands.Context, discord.Interaction],
        error_msg: str,
        should_trace: bool = False,
        exception: Exception = None,
    ) -> Optional[discord.Message]:
        """send a formatted error message to the context

        Args:
            ctx: The command context or interaction
            error_msg: The error message to display
            should_trace: Whether to include traceback info
            exception: The actual exception object (if available)

        Returns:
            The sent message, if any
        """
        embed = self.error_embed(description=error_msg)

        if should_trace and exception:
            tb = traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
            tb_text = "".join(tb)

            if len(tb_text) > 1000:
                tb_text = f"{tb_text[:997]}..."

            embed.add_field(
                name="traceback", value=f"```py\n{tb_text}\n```", inline=False
            )

        if isinstance(ctx, commands.Context):
            return await ctx.reply(embed=embed)
        elif isinstance(ctx, discord.Interaction):
            if ctx.response.is_done():
                return await ctx.followup.send(embed=embed, ephemeral=True)
            else:
                await ctx.response.send_message(embed=embed, ephemeral=True)
                return await ctx.original_response()
        return None

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        """handle command errors (prefix commands)"""
        if hasattr(ctx, "handled_error") and ctx.handled_error:
            return

        if hasattr(error, "original"):
            error = error.original

        self.logger.error(f"Command error in {ctx.command}: {error}", exc_info=error)

        if isinstance(error, commands.CommandNotFound):
            if not ctx.guild:
                return
            invoked_with = ctx.invoked_with.lower()
            aliases = await db.get_aliases(ctx.guild.id)
            if aliases:
                alias_command = next(
                    (
                        a["command"]
                        for a in aliases
                        if a["alias"].lower() == invoked_with
                    ),
                    None,
                )
                if alias_command:
                    aliased_command = " ".join(alias_command)
                new_content = ctx.prefix + aliased_command

                if ctx.message.content.strip() != ctx.prefix + ctx.invoked_with:
                    args = ctx.message.content[
                        len(ctx.prefix + ctx.invoked_with) :
                    ].strip()
                    new_content += " " + args

                new_message = copy.copy(ctx.message)
                new_message.content = new_content

                new_ctx = await self.bot.get_context(new_message)

                if new_ctx.command is None:
                    await ctx.send(
                        f"the aliased command **{aliased_command}** was not found"
                    )
                    return

                try:
                    await new_ctx.command.invoke(new_ctx)
                except Exception as e:
                    print(e)
                    await self.on_command_error(new_ctx, e)

        elif isinstance(error, commands.MissingRequiredArgument):
            param_name = error.param.name
            await self._send_error_message(
                ctx,
                f"the `{param_name}` argument is required. check `{config.PREFIX}help {ctx.command}` for usage.",
                exception=error,
            )

        elif isinstance(error, commands.BadArgument):
            await self._send_error_message(
                ctx,
                f"invalid argument: {str(error)}",
                exception=error,
            )

        elif isinstance(error, commands.MissingPermissions):
            perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
            await self._send_error_message(
                ctx,
                f"you need {perms} permission(s) to use this command.",
                exception=error,
            )

        elif isinstance(error, commands.BotMissingPermissions):
            perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
            await self._send_error_message(
                ctx,
                f"i need {perms} permission(s) to execute this command.",
                exception=error,
            )

        elif isinstance(error, commands.NotOwner):
            return

        elif isinstance(error, commands.CommandOnCooldown):
            await self._send_error_message(
                ctx,
                f"this command is on cooldown. try again in {error.retry_after:.2f}s.",
                exception=error,
            )

        elif isinstance(error, commands.MaxConcurrencyReached):
            await self._send_error_message(
                ctx,
                f"this command is already being used by the maximum number of users. ({error.number} {error.per.name})",
                exception=error,
            )

        elif isinstance(error, commands.DisabledCommand):
            await self._send_error_message(
                ctx,
                "this command is currently disabled.",
                exception=error,
            )

        elif isinstance(error, commands.NoPrivateMessage):
            await self._send_error_message(
                ctx,
                "this command can only be used in servers, not private messages.",
                exception=error,
            )

        elif isinstance(error, commands.PrivateMessageOnly):
            await self._send_error_message(
                ctx,
                "this command can only be used in private messages, not servers.",
                exception=error,
            )

        elif isinstance(error, commands.CheckFailure):
            await self._send_error_message(
                ctx,
                "you do not have permission to use this command.",
                exception=error,
            )

        elif isinstance(error, commands.TooManyArguments):
            await self._send_error_message(
                ctx,
                f"too many arguments provided for `{ctx.command}`. check `{config.PREFIX}help {ctx.command}` for usage.",
                exception=error,
            )

        else:
            self.logger.error("Unhandled command error", exc_info=error)

            await self._log_to_channel(ctx, error)

            is_owner = await self.bot.is_owner(ctx.author)

            await self._send_error_message(
                ctx,
                "an unexpected error occurred while executing this command. please try again later.",
                should_trace=is_owner,
                exception=error,
            )

    @commands.Cog.listener()
    async def on_application_command_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        """handle application command errors (slash commands)"""
        command_name = interaction.command.name if interaction.command else "Unknown"

        if hasattr(error, "original"):
            error = error.original

        self.logger.error(
            f"slash command error in {command_name}: {error}", exc_info=error
        )

        if isinstance(error, discord.app_commands.MissingPermissions):
            perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
            await self._send_error_message(
                interaction,
                f"you need {perms} permission(s) to use this command.",
                exception=error,
            )

        elif isinstance(error, discord.app_commands.BotMissingPermissions):
            perms = ", ".join(f"`{p}`" for p in error.missing_permissions)
            await self._send_error_message(
                interaction,
                f"i need {perms} permission(s) to execute this command.",
                exception=error,
            )

        elif isinstance(error, discord.app_commands.CommandOnCooldown):
            await self._send_error_message(
                interaction,
                f"this command is on cooldown. try again in {error.retry_after:.2f}s.",
                exception=error,
            )

        elif isinstance(error, discord.app_commands.CheckFailure):
            await self._send_error_message(
                interaction,
                "you do not have permission to use this command.",
                exception=error,
            )

        else:
            self.logger.error("Unhandled slash command error", exc_info=error)

            await self._log_to_channel(interaction, error)

            is_owner = await self.bot.is_owner(interaction.user)

            await self._send_error_message(
                interaction,
                "an unexpected error occurred while executing this command. please try again later.",
                should_trace=is_owner,
                exception=error,
            )

    async def _log_to_channel(self, ctx, error):
        """log an error to a channel if configured"""
        try:
            error_channel_id = getattr(self.bot, "error_channel_id", None)
            if not error_channel_id:
                return

            channel = self.bot.get_channel(error_channel_id)
            if not channel:
                return

            embed = discord.Embed(
                color=config.ERROR_COLOR,
                timestamp=discord.utils.utcnow(),
            )

            if isinstance(ctx, commands.Context):
                embed.add_field(
                    name="command info",
                    value=(
                        f"Command: `{ctx.command}`\n"
                        f"Channel: {ctx.channel.mention} (`{ctx.channel.id}`)\n"
                        f"User: {ctx.author.mention} (`{ctx.author.id}`)\n"
                        f"Guild: `{ctx.guild.name if ctx.guild else 'DM'}` (`{ctx.guild.id if ctx.guild else 'N/A'}`)"
                    ),
                    inline=False,
                )
                embed.add_field(
                    name="message",
                    value=f"```\n{ctx.message.content[:1000]}\n```",
                    inline=False,
                )
            elif isinstance(ctx, discord.Interaction):
                command_name = ctx.command.name if ctx.command else "Unknown"
                embed.add_field(
                    name="command info",
                    value=(
                        f"Command: `{command_name}`\n"
                        f"Channel: {ctx.channel.mention} (`{ctx.channel.id}`)\n"
                        f"User: {ctx.user.mention} (`{ctx.user.id}`)\n"
                        f"Guild: `{ctx.guild.name if ctx.guild else 'DM'}` (`{ctx.guild.id if ctx.guild else 'N/A'}`)"
                    ),
                    inline=False,
                )

            embed.add_field(
                name="error type", value=f"`{type(error).__name__}`", inline=False
            )

            tb = traceback.format_exception(type(error), error, error.__traceback__)
            tb_text = "".join(tb)

            if len(tb_text) > 1000:
                chunks = [tb_text[i : i + 1000] for i in range(0, len(tb_text), 1000)]
                for i, chunk in enumerate(chunks):
                    embed.add_field(
                        name=f"traceback part {i + 1}/{len(chunks)}",
                        value=f"```py\n{chunk}\n```",
                        inline=False,
                    )
            else:
                embed.add_field(
                    name="traceback", value=f"```py\n{tb_text}\n```", inline=False
                )

            await channel.send(embed=embed)

        except Exception as e:
            self.logger.error(f"Failed to log error to channel: {e}", exc_info=e)

    @commands.command(name="error", hidden=True)
    @commands.is_owner()
    async def force_error(self, ctx, error_type: str = None):
        """owner command to test the error handler with different error types"""
        if error_type == "basic":
            raise Exception("This is a basic error for testing")
        elif error_type == "command":
            raise commands.CommandError("This is a command error for testing")
        elif error_type == "missing_arg":
            raise commands.MissingRequiredArgument(ctx.command.params["error_type"])
        elif error_type == "bad_arg":
            raise commands.BadArgument("This argument is bad for testing")
        elif error_type == "missing_perm":
            raise commands.MissingPermissions(["manage_messages"])
        elif error_type == "bot_missing_perm":
            raise commands.BotMissingPermissions(["manage_messages"])
        elif error_type == "not_owner":
            raise commands.NotOwner("You are not the owner")
        elif error_type == "cooldown":
            raise commands.CommandOnCooldown(commands.Cooldown(1, 60), 30)
        elif error_type == "max_concurrency":
            raise commands.MaxConcurrencyReached(
                commands.MaxConcurrency(1, commands.BucketType.user)
            )
        elif error_type == "disabled":
            raise commands.DisabledCommand("This command is disabled")
        elif error_type == "no_dm":
            raise commands.NoPrivateMessage("This command cannot be used in DMs")
        elif error_type == "dm_only":
            raise commands.PrivateMessageOnly("This command can only be used in DMs")
        elif error_type == "check_failure":
            raise commands.CheckFailure("Check failed")
        elif error_type == "too_many_args":
            raise commands.TooManyArguments("Too many arguments provided for testing")
        else:
            await ctx.reply(
                embed=self.embed(
                    title="error tester",
                    description=(
                        "available error types:\n"
                        "`basic`, `command`, `missing_arg`, `bad_arg`, `missing_perm`, "
                        "`bot_missing_perm`, `not_owner`, `cooldown`, `max_concurrency`, "
                        "`disabled`, `no_dm`, `dm_only`, `check_failure`, `too_many_args`"
                    ),
                )
            )

    @commands.command(name="error_channel", hidden=True)
    @commands.is_owner()
    async def set_error_channel(self, ctx, channel: discord.TextChannel = None):
        """set or view the channel for error logging"""
        if channel:
            self.bot.error_channel_id = channel.id
            await ctx.reply(
                embed=self.success_embed(
                    description=f"error channel set to {channel.mention}"
                )
            )
        else:
            error_channel_id = getattr(self.bot, "error_channel_id", None)
            if error_channel_id:
                channel = self.bot.get_channel(error_channel_id)
                if channel:
                    await ctx.reply(
                        embed=self.embed(
                            description=f"current error channel: {channel.mention}"
                        )
                    )
                else:
                    await ctx.reply(
                        embed=self.warning_embed(
                            description=f"error channel is set to ID `{error_channel_id}` but I cannot access it"
                        )
                    )
            else:
                await ctx.reply(
                    embed=self.warning_embed(description="no error channel is set")
                )


async def setup(bot):
    await bot.add_cog(ErrorHandler(bot))
