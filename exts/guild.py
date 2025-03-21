import discord
from discord.ext import commands
from discord import Permissions
from core.basecog import BaseCog
import datetime


class Guild(BaseCog):
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):
        """Make a channel read-only"""
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send(
            embed=self.success_embed(
                description=f"{ctx.channel.mention} has been locked."
            )
        )

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        """Unlock a channel"""
        await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send(
            embed=self.success_embed(
                description=f"{ctx.channel.mention} has been unlocked."
            )
        )

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def hide(self, ctx):
        """Hide a channel from members"""
        await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=False)
        await ctx.send(
            embed=self.success_embed(
                description=f"{ctx.channel.mention} has been hidden."
            )
        )

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def show(self, ctx):
        """Show a hidden channel"""
        await ctx.channel.set_permissions(ctx.guild.default_role, view_channel=True)
        await ctx.send(
            embed=self.success_embed(
                description=f"{ctx.channel.mention} is now visible."
            )
        )

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, seconds: int):
        """Set slowmode for a channel"""
        if seconds < 0 or seconds > 21600:
            return await ctx.send(
                embed=self.error_embed(
                    description="slowmode must be between 0 and 21600 seconds."
                )
            )
        await ctx.channel.edit(slowmode_delay=seconds)

        if seconds > 0:
            await ctx.send(
                embed=self.success_embed(
                    description=f"{ctx.channel.mention} slowmode set to {seconds} seconds"
                )
            )
        else:
            await ctx.send(
                embed=self.success_embed(
                    description=f"{ctx.channel.mention} slowmode disabled"
                )
            )

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, *args):
        """Delete messages in a channel"""
        await ctx.message.delete()

        if not args:
            deleted = await ctx.channel.purge(limit=5)
            await ctx.send(
                embed=self.success_embed(
                    description=f"Deleted {len(deleted)} messages."
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
                        description=f"deleted {len(deleted)} messages."
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

            remaining = limit - deleted_count

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
                    description=f"deleted {len(messages_to_delete)} messages."
                ),
                delete_after=10,
            )
        else:
            await ctx.send(
                embed=self.warning_embed(
                    description="no messages matched your criteria."
                ),
                delete_after=10,
            )


async def setup(bot):
    await bot.add_cog(Guild(bot))
