import asyncio
import datetime
from io import BytesIO

import discord
import timeago
from discord.ext import commands
from rembg import remove

import config
from core.basecog import BaseCog
from core.database import db
from core.utils import would_invoke


class Misc(BaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self._afk_cd_mapping = commands.CooldownMapping.from_cooldown(
            1, 45.0, commands.BucketType.user
        )

    @commands.command(
        name="rembg", aliases=["removebg", "rmbg"], brief="remove background from image"
    )
    async def rembg(self, ctx, url=None):
        """remove background from image"""
        image_data = None

        if url:
            async with self.bot.session.get(url) as resp:
                if resp.status == 200:
                    image_data = await resp.read()
                else:
                    return await ctx.reply(
                        embed=self.error_embed(description="could not get image")
                    )

        elif ctx.message.reference:
            message = ctx.message.reference.resolved
            if not message:
                return await ctx.reply(
                    embed=self.error_embed(description="invalid message")
                )
            if message.attachments:
                image_data = await message.attachments[0].read()

        elif ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            if attachment.content_type.startswith("image/"):
                image_data = await attachment.read()
            else:
                return await ctx.reply(
                    embed=self.error_embed(description="not an image")
                )

        if not image_data:
            return await ctx.reply(embed=self.error_embed(description="no image found"))

        await ctx.message.add_reaction(config.THINK_ICON)
        try:
            output = await asyncio.to_thread(remove, image_data)
            buffer = BytesIO(output)
            await ctx.reply(file=discord.File(buffer, filename="rembg.png"))
        finally:
            await ctx.message.remove_reaction(config.THINK_ICON, self.bot.user)

    @commands.command(name="afk", brief="set your status to AFK")
    async def afk(self, ctx, *, message: str = None):
        """set your status to AFK"""
        message = message or "AFK"
        await db.set_afk(user_id=ctx.author.id, guild_id=ctx.guild.id, message=message)
        await ctx.reply(
            embed=self.success_embed(
                description=f"{ctx.author.mention} set AFK status for: **{message}**"
            )
        )

    @commands.Cog.listener(name="on_message")
    async def afk_on_message(self, message):
        if message.author.bot or not message.guild:
            return

        if await would_invoke(self.bot, message, command_name="afk"):
            return

        author_afk = await db.get_afk(
            user_id=message.author.id, guild_id=message.guild.id
        )
        if author_afk:
            await db.remove_afk(user_id=message.author.id, guild_id=message.guild.id)
            await message.channel.send(
                embed=self.embed(
                    description=f"<@{message.author.id}> welcome back"
                ).set_footer(
                    text=f"AFK since {timeago.format(author_afk['created_at'].replace(tzinfo=None), datetime.datetime.utcnow())}"
                )
            )

        afk_users = await db.get_guild_afk(guild_id=message.guild.id)
        if not afk_users:
            return

        for row in afk_users:
            mentioned_user_id = row["user_id"]
            mentioned_discord_user = message.guild.get_member(mentioned_user_id)
            if mentioned_discord_user and mentioned_discord_user in message.mentions:
                bucket = self._afk_cd_mapping.get_bucket(message)
                retry_after = bucket.update_rate_limit()
                if retry_after:
                    continue

                await message.reply(
                    embed=self.warning_embed(
                        description=f"<@{mentioned_user_id}> is AFK for: **{row['message']}**"
                    ).set_footer(
                        text=f"AFK since {timeago.format(row['created_at'].replace(tzinfo=None), datetime.datetime.utcnow())}"
                    )
                )


async def setup(bot):
    await bot.add_cog(Misc(bot))
