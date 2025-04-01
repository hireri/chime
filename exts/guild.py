import datetime

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
                    description=f"{ctx.channel.mention} deleted **{len(deleted)}** messages"
                ),
                delete_after=10,
            )
            return

        if len(args) == 1 and args[0].isdigit():
            try:
                limit = int(args[0])
                deleted = await ctx.channel.purge(limit=limit)
                await ctx.send(
                    embed=self.success_embed(
                        description=f"{ctx.channel.mention} deleted **{len(deleted)}** messages"
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
                user = ctx.guild.get_member(user_id)
                if user:
                    users.append(user)
                    continue
            except ValueError:
                pass

            try:
                channel_id = int(arg.strip("<#>"))
                channel = ctx.guild.get_channel(channel_id)
                if channel:
                    channels.append(channel)
                    continue
            except ValueError:
                pass

            try:
                limit_val = int(arg)
                limit = limit_val
                continue
            except ValueError:
                pass

            if arg in ["bot", "bots"]:
                constraints.append(lambda m: m.author.bot)

        if not channels:
            channels = [ctx.channel]

        def check_message(message):
            if message.channel not in channels:
                return False

            if users and message.author not in users:
                return False

            for constraint in constraints:
                if not constraint(message):
                    return False

            return True

        deleted_count = 0
        messages_to_delete = []
        search_limit = min(limit * 5, 1000)

        for channel in channels:
            if deleted_count >= limit:
                break

            async for message in channel.history(limit=search_limit):
                if check_message(message):
                    messages_to_delete.append(message)
                    deleted_count += 1
                    if deleted_count >= limit:
                        break

        if messages_to_delete:
            two_weeks_ago = datetime.datetime.now(
                datetime.timezone.utc
            ) - datetime.timedelta(days=14)
            recent_messages = [
                msg for msg in messages_to_delete if msg.created_at > two_weeks_ago
            ]
            old_messages = [
                msg for msg in messages_to_delete if msg.created_at <= two_weeks_ago
            ]

            channel_messages = {}
            for msg in recent_messages:
                if msg.channel not in channel_messages:
                    channel_messages[msg.channel] = []
                channel_messages[msg.channel].append(msg)

            for channel, msgs in channel_messages.items():
                if msgs:
                    await channel.delete_messages(msgs)

            for message in old_messages:
                await message.delete()

            await ctx.send(
                embed=self.success_embed(
                    description=f"deleted **{len(messages_to_delete)}** messages"
                ),
                delete_after=10,
            )
        else:
            await ctx.send(
                embed=self.warning_embed(
                    description="no messages matched your criteria"
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
