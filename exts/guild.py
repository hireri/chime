import discord
from discord.ext import commands

import config
from core.basecog import BaseCog


class Guild(BaseCog):
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx, *channels: discord.TextChannel | discord.VoiceChannel):
        """make channel read-only"""
        channels = channels or [ctx.channel]
        if len(channels) > 1:
            await ctx.message.add_reaction(config.THINK_ICON)

        for channel in channels:
            await channel.set_permissions(ctx.guild.default_role, send_messages=False)

        if len(channels) == 1:
            await ctx.reply(
                embed=self.success_embed(
                    description=f"{channels[0].mention} has been **locked**"
                )
            )
        else:
            await ctx.message.remove_reaction(config.THINK_ICON, self.bot.user)
            await ctx.reply(
                embed=self.success_embed(
                    description=f"**{len(channels)}** channels have been **locked**"
                )
            )

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx, *channels: discord.TextChannel | discord.VoiceChannel):
        """unlock channel"""
        channels = channels or [ctx.channel]
        if len(channels) > 1:
            await ctx.message.add_reaction(config.THINK_ICON)

        for channel in channels:
            await channel.set_permissions(ctx.guild.default_role, send_messages=True)

        if len(channels) == 1:
            await ctx.reply(
                embed=self.success_embed(
                    description=f"{channels[0].mention} has been **unlocked**"
                )
            )
        else:
            await ctx.message.remove_reaction(config.THINK_ICON, self.bot.user)
            await ctx.reply(
                embed=self.success_embed(
                    description=f"**{len(channels)}** channels have been **unlocked**"
                )
            )

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def hide(self, ctx, *channels: discord.TextChannel | discord.VoiceChannel):
        """hide channel from members"""
        channels = channels or [ctx.channel]
        if len(channels) > 1:
            await ctx.message.add_reaction(config.THINK_ICON)
        for channel in channels:
            await channel.set_permissions(ctx.guild.default_role, view_channel=False)

        if len(channels) == 1:
            await ctx.reply(
                embed=self.success_embed(
                    description=f"{channels[0].mention} has been **hidden**"
                )
            )
        else:
            await ctx.message.remove_reaction(config.THINK_ICON, self.bot.user)
            await ctx.reply(
                embed=self.success_embed(
                    description=f"**{len(channels)}** channels have been **hidden**"
                )
            )

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def show(self, ctx, *channels: discord.TextChannel | discord.VoiceChannel):
        """show hidden channel"""
        channels = channels or [ctx.channel]
        if len(channels) > 1:
            await ctx.message.add_reaction(config.THINK_ICON)
        for channel in channels:
            await channel.set_permissions(ctx.guild.default_role, view_channel=True)

        if len(channels) == 1:
            await ctx.reply(
                embed=self.success_embed(
                    description=f"{channels[0].mention} is now **visible**"
                )
            )
        else:
            await ctx.message.remove_reaction(config.THINK_ICON, self.bot.user)
            await ctx.reply(
                embed=self.success_embed(
                    description=f"**{len(channels)}** channels are now **visible**"
                )
            )

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def slowmode(
        self,
        ctx,
        seconds: int,
        *channels: discord.TextChannel | discord.VoiceChannel,
    ):
        """set slowmode for channel"""
        if seconds < 0 or seconds > 21600:
            return await ctx.reply(
                embed=self.error_embed(
                    description="slowmode must be between 0 and 21600 seconds"
                )
            )

        channels = channels or [ctx.channel]
        if len(channels) > 1:
            await ctx.message.add_reaction(config.THINK_ICON)

        for channel in channels:
            await channel.edit(slowmode_delay=seconds)

        if seconds > 0:
            if len(channels) > 1:
                await ctx.message.remove_reaction(config.THINK_ICON, self.bot.user)
                await ctx.reply(
                    embed=self.success_embed(
                        description=f"**{len(channels)}** channels have **{seconds}s slowmode**"
                    )
                )
            else:
                await ctx.reply(
                    embed=self.success_embed(
                        description=f"{ctx.channel.mention} slowmode set to **{seconds} seconds**"
                    )
                )
        else:
            if len(channels) > 1:
                await ctx.message.remove_reaction(config.THINK_ICON, self.bot.user)
                await ctx.reply(
                    embed=self.success_embed(
                        description=f"**{len(channels)}** channels have **disabled slowmode**"
                    )
                )
            else:
                await ctx.reply(
                    embed=self.success_embed(
                        description=f"{ctx.channel.mention} slowmode **disabled**"
                    )
                )

    @commands.command(name="slowall", brief="Set slowmode for all channels")
    @commands.has_permissions(manage_channels=True)
    async def slowall(self, ctx, seconds: int):
        """set slowmode for all channels"""
        if seconds < 0 or seconds > 21600:
            return await ctx.reply(
                embed=self.error_embed(
                    description="slowmode must be between 0 and 21600 seconds"
                )
            )

        await ctx.message.add_reaction(config.THINK_ICON)

        everyone_role = ctx.guild.default_role
        for channel in ctx.guild.channels:
            if channel.overwrites_for(everyone_role).send_messages is False:
                continue
            await channel.edit(slowmode_delay=seconds)

        await ctx.message.remove_reaction(config.THINK_ICON, self.bot.user)

        if seconds > 0:
            await ctx.reply(
                embed=self.success_embed(
                    description=f"slowmode set to **{seconds} seconds** for all channels"
                )
            )
        else:
            await ctx.reply(
                embed=self.success_embed(
                    description="slowmode **disabled** for all channels"
                )
            )

    @commands.command(
        name="purge",
        brief="delete messages in a channel",
        aliases=["prune", "clear", "p", "c"],
    )
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, *args):
        """delete messages in channel"""
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            pass

        limit = 5
        users = []
        channels = []
        constraints = []

        if not args:
            try:
                deleted = await ctx.channel.purge(limit=limit)
                await self._send_purge_success(ctx, ctx.channel, len(deleted))
                return
            except Exception as e:
                return await self._send_purge_error(ctx, ctx.channel, e)

        if len(args) == 1 and args[0].isdigit():
            try:
                limit = min(int(args[0]), 2000)
                deleted = await ctx.channel.purge(limit=limit)
                await self._send_purge_success(ctx, ctx.channel, len(deleted))
                return
            except Exception as e:
                return await self._send_purge_error(ctx, ctx.channel, e)

        async with ctx.channel.typing():
            for arg in args:
                if arg.startswith("<@") and arg.endswith(">"):
                    try:
                        user_id = int(arg.strip("<@!>"))
                        user = ctx.guild.get_member(user_id)
                        if not user:
                            try:
                                user = await ctx.guild.fetch_member(user_id)
                            except (discord.NotFound, discord.HTTPException):
                                continue
                        if user:
                            users.append(user)
                            continue
                    except ValueError:
                        pass

                if arg.startswith("<#") and arg.endswith(">"):
                    try:
                        channel_id = int(arg.strip("<#>"))
                        channel = ctx.guild.get_channel(channel_id)
                        if isinstance(channel, discord.TextChannel):
                            channels.append(channel)
                            continue
                    except ValueError:
                        pass

                if arg.isdigit():
                    limit_val = int(arg)
                    if limit_val > 0:
                        limit = min(limit_val, 2000)
                        continue

                if arg.lower() in ["bot", "bots"]:
                    constraints.append(lambda m: m.author.bot)

            if not channels:
                channels = [ctx.channel]

            def check_message(message):
                if message.id == ctx.message.id:
                    return False

                if users and message.author not in users:
                    return False

                for constraint in constraints:
                    if not constraint(message):
                        return False

                return True

            total_deleted = 0
            errors = []

            for channel in channels:
                try:
                    messages_to_delete = []
                    search_limit = min(limit * 3, 1000)

                    async for message in channel.history(limit=search_limit):
                        if check_message(message):
                            messages_to_delete.append(message)
                            if len(messages_to_delete) >= limit:
                                break

                    if not messages_to_delete:
                        continue

                    import datetime

                    two_weeks_ago = datetime.datetime.now(
                        datetime.timezone.utc
                    ) - datetime.timedelta(days=14)

                    recent_messages = [
                        msg
                        for msg in messages_to_delete
                        if msg.created_at > two_weeks_ago
                    ]
                    old_messages = [
                        msg
                        for msg in messages_to_delete
                        if msg.created_at <= two_weeks_ago
                    ]

                    if recent_messages:
                        if len(recent_messages) == 1:
                            await recent_messages[0].delete()
                            total_deleted += 1
                        else:
                            deleted = await channel.delete_messages(recent_messages)
                            total_deleted += len(recent_messages)

                    for old_msg in old_messages:
                        try:
                            await old_msg.delete()
                            total_deleted += 1
                        except (
                            discord.Forbidden,
                            discord.NotFound,
                            discord.HTTPException,
                        ):
                            pass

                except discord.Forbidden:
                    errors.append(f"Missing permissions in {channel.mention}")
                except discord.HTTPException as e:
                    errors.append(f"Error in {channel.mention}: {str(e)}")
                except Exception as e:
                    errors.append(f"Unexpected error in {channel.mention}: {str(e)}")

            if total_deleted == 0:
                if errors:
                    error_msg = "\n".join(errors)
                    await ctx.send(
                        embed=self.error_embed(
                            description=f"Failed to delete messages:\n{error_msg}"
                        ),
                        delete_after=10,
                    )
                else:
                    await ctx.send(
                        embed=self.warning_embed(
                            description="No messages matched your criteria"
                        ),
                        delete_after=10,
                    )
            else:
                plural = "" if total_deleted == 1 else "s"
                await ctx.send(
                    embed=self.success_embed(
                        description=f"Deleted **{total_deleted}** message{plural}"
                    ),
                    delete_after=10,
                )

    async def _send_purge_success(self, ctx, channel, count):
        """helper method send purge success message"""
        plural = "" if count == 1 else "s"
        await ctx.send(
            embed=self.success_embed(
                description=f"{channel.mention} deleted **{count}** message{plural}"
            ),
            delete_after=10,
        )

    async def _send_purge_error(self, ctx, channel, error):
        """helper method send purge error message"""
        await ctx.send(
            embed=self.error_embed(
                description=f"Failed to delete messages in {channel.mention}: {str(error)}"
            ),
            delete_after=10,
        )

    @commands.command(
        name="lockdown", brief="Lockdown all channels", aliases=["lockall", "unlockall"]
    )
    @commands.has_permissions(manage_channels=True)
    async def lockdown(self, ctx):
        """make all channels read-only"""
        role = ctx.guild.default_role
        perms = role.permissions

        if not perms.send_messages:
            perms.update(send_messages=True)
            await role.edit(permissions=perms)
            await ctx.reply(
                embed=self.success_embed(description="the server is now **unlocked**")
            )
        else:
            perms.update(send_messages=False)
            await role.edit(permissions=perms)
            await ctx.reply(
                embed=self.success_embed(description="the server is in **lockdown**")
            )

    @commands.command(
        name="invites", brief="view invites for the server", aliases=["inv", "invite"]
    )
    @commands.has_permissions(manage_guild=True)
    async def invites(self, ctx):
        """view invites for server"""
        invites = await ctx.guild.invites()
        if not invites:
            return await ctx.reply(
                embed=self.error_embed(
                    description="this server doesn't have any invites"
                )
            )
        invites_per_page = 10
        pages = []
        for i in range(0, len(invites), invites_per_page):
            page = invites[i : i + invites_per_page]

            embed = self.embed(
                description="\n".join(
                    f"- **[{invite.code}]({invite.url})** expires {discord.utils.format_dt(invite.expires_at, style='R') if invite.expires_at else '`never`'} {invite.inviter.mention}"
                    for invite in page
                    if not invite.revoked
                )
            ).set_author(
                name=f"{ctx.guild.name}'s invites", icon_url=ctx.guild.icon.url
            )

            embed.set_footer(
                text=f"vanity: .gg/{ctx.guild.vanity_url_code}"
                if ctx.guild.vanity_url_code
                else "no vanity url"
            )
            pages.append(embed)
        await self.paginate(ctx, pages)


async def setup(bot):
    await bot.add_cog(Guild(bot))
