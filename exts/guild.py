import discord
from discord.ext import commands

import config
from core.basecog import BaseCog


class Guild(BaseCog):
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx, *channels: discord.TextChannel | discord.VoiceChannel):
        """Make a channel read-only"""
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
        """Unlock a channel"""
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
        """Hide a channel from members"""
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
        """Show a hidden channel"""
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
        """Set slowmode for a channel"""
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
        """Set slowmode for all channels"""
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
        """Delete messages in a channel"""
        await ctx.message.delete()

        if not args:
            deleted = await ctx.channel.purge(limit=5)
            await ctx.send(
                embed=self.success_embed(
                    description=f"{ctx.channel.mention} deleted **{len(deleted)}** message{'s' * (len(deleted) != 1)}"
                ),
                delete_after=10,
            )
            return

        async with ctx.channel.typing():
            if len(args) == 1 and args[0].isdigit():
                try:
                    limit = int(args[0])
                    deleted = await ctx.channel.purge(limit=limit)
                    await ctx.send(
                        embed=self.success_embed(
                            description=f"{ctx.channel.mention} deleted **{len(deleted)}** message{'s' * (len(deleted) != 1)}"
                        ),
                        delete_after=10,
                    )
                    return
                except ValueError:
                    pass

            constraints = []
            users = []
            channels = []
            limit = 5

            for arg in args:
                try:
                    user_id = int(arg.strip("<@!>"))
                    user = ctx.guild.get_member(
                        user_id
                    ) or await ctx.guild.fetch_member(user_id)
                    if user:
                        users.append(user)
                        continue
                except (ValueError, discord.NotFound, discord.HTTPException):
                    pass

                try:
                    channel_id = int(arg.strip("<#>"))
                    channel = ctx.guild.get_channel(channel_id)
                    if isinstance(channel, discord.TextChannel):
                        channels.append(channel)
                        continue
                except (ValueError, AttributeError):
                    pass

                try:
                    limit_val = int(arg)
                    if limit_val > 0:
                        limit = min(limit_val, 2000)
                    continue
                except ValueError:
                    pass

                if arg.lower() in ["bot", "bots"]:
                    constraints.append(lambda m: m.author.bot)
                # add more constraints here

            if not channels:
                channels = [ctx.channel]

            def check_message(message: discord.Message) -> bool:
                if users and message.author not in users:
                    return False

                if not all(constraint(message) for constraint in constraints):
                    return False

                return True

            messages_to_delete = []
            search_depth = min(limit * 5, 1000)

            for channel in channels:
                if len(messages_to_delete) >= limit:
                    break

                try:
                    async for message in channel.history(limit=search_depth):
                        if check_message(message):
                            messages_to_delete.append(message)
                            if len(messages_to_delete) >= limit:
                                break
                except discord.Forbidden:
                    print(f"missing permissions to read history in {channel.mention}")
                    continue
                except discord.HTTPException as e:
                    print(f"error fetching history in {channel.mention}: {e}")
                    continue

            messages_to_delete = messages_to_delete[:limit]

            if not messages_to_delete:
                await ctx.send(
                    embed=self.warning_embed(
                        description="no messages matched your criteria"
                    ),
                    delete_after=10,
                )
                return

            grouped_messages = {}
            for msg in messages_to_delete:
                if msg.channel not in grouped_messages:
                    grouped_messages[msg.channel] = []
                grouped_messages[msg.channel].append(msg)

            total_deleted_count = 0
            for channel, msgs in grouped_messages.items():
                try:
                    await channel.delete_messages(msgs)
                    total_deleted_count += len(msgs)
                except discord.Forbidden:
                    await ctx.send(
                        embed=self.error_embed(
                            description=f"missing permissions to delete messages in {channel.mention}"
                        ),
                        delete_after=10,
                    )
                except discord.HTTPException as e:
                    await ctx.send(
                        embed=self.error_embed(
                            description=f"Failed to delete messages in {channel.mention}: {e}"
                        ),
                        delete_after=10,
                    )
                except discord.NotFound:
                    pass

            await ctx.send(
                embed=self.success_embed(
                    description=f"deleted **{total_deleted_count}** message{'s' * (len(total_deleted_count) != 1)}"
                ),
                delete_after=10,
            )

    @commands.command(
        name="lockdown", brief="Lockdown all channels", aliases=["lockall", "unlockall"]
    )
    @commands.has_permissions(manage_channels=True)
    async def lockdown(self, ctx):
        """Make all channels read-only"""
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
        """view invites for the server"""
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
