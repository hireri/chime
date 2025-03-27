import re
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from urllib.parse import urlparse, urlunparse
import dotenv

import discord
import logging
import config
from discord.ext import commands

from core.basecog import BaseCog

logger = logging.getLogger(__name__)
dotenv.load_dotenv()


class Snipe(BaseCog):
    def __init__(self, bot):
        self.message_history: Dict[int, List[Tuple[discord.Message, datetime]]] = {}
        self.edit_history: Dict[
            int, List[Tuple[discord.Message, discord.Message, datetime]]
        ] = {}
        self.reaction_history: Dict[
            int,
            List[Tuple[discord.Message, discord.Reaction, discord.Member, datetime]],
        ] = {}
        self.ttl = timedelta(minutes=5)
        self.image_regex = re.compile(
            r"(https?://(?:cdn\.discordapp\.com|media\.discordapp\.net|i\.imgur\.com)/\S+\.(?:jpg|jpeg|png|gif|webp)(?:\?\S+)?)"
        )
        self.tenor_regex = re.compile(r"(https?://(?:tenor\.com/view/[a-zA-Z0-9-]+))")
        self.giphy_regex = re.compile(
            r"(https?://(?:media\.giphy\.com/media/[a-zA-Z0-9]+/giphy\.gif))"
        )
        super().__init__(bot)

    def clean_url(self, url):
        parsed = urlparse(url)
        cleaned = urlunparse(parsed._replace(query=""))
        return cleaned

    async def get_tenor_gif_url(self, gif_url: str) -> str:
        if "tenor.com" in gif_url:
            gif_id = gif_url.split("-")[-1]
            async with self.bot.session.get(
                f"https://tenor.googleapis.com/v2/posts?ids={
                    gif_id}&key={os.getenv("TENOR")}"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data["results"][0]["media_formats"]["gif"]["url"]
        return gif_url

    async def create_snipe_embed(
        self,
        content: str,
        author: discord.Member,
        attachments: List[discord.Attachment],
    ) -> List[discord.Embed]:
        self.image_urls = []

        def replace_link(match, link_type):
            url = self.clean_url(match.group(1))
            self.image_urls.append(url)
            return f"[{link_type} {len(self.image_urls)}]({url})"

        content = self.image_regex.sub(lambda m: replace_link(m, "Image"), content)
        content = self.tenor_regex.sub(lambda m: replace_link(m, "GIF"), content)
        content = self.giphy_regex.sub(lambda m: replace_link(m, "GIF"), content)

        base_embed = discord.Embed(
            description=content,
            timestamp=datetime.utcnow(),
            url="https://discord.com",
            color=config.MAIN_COLOR,
        )
        base_embed.set_author(
            name=author.display_name, icon_url=author.display_avatar.url
        )

        all_images = self.image_urls + [
            att.url
            for att in attachments
            if att.filename.split(".")[-1].lower()
            in ["jpg", "jpeg", "gif", "png", "webp"]
        ]

        embeds = [base_embed]
        for i, img_url in enumerate(all_images):
            if i % 4 == 0 and i > 0:

                new_base_embed = discord.Embed(
                    url=f"https://discord.com/images/{i//4}",
                    description=f"Additional images ({
                        i+1}-{min(i+4, len(all_images))})",
                    color=config.MAIN_COLOR,
                )
                embeds.append(new_base_embed)

            new_embed = discord.Embed(url=embeds[-1].url, color=config.MAIN_COLOR)
            new_embed.set_image(url=img_url)
            embeds.append(new_embed)

        return embeds or []

    @commands.Cog.listener(name="on_message_delete")
    async def log_delete(self, message):
        if message.guild and not message.author.bot:
            self.message_history.setdefault(message.channel.id, []).append(
                (message, datetime.utcnow())
            )

    @commands.Cog.listener(name="on_message_edit")
    async def log_edit(self, before, after):
        if before.guild and not before.author.bot:
            self.edit_history.setdefault(before.channel.id, []).append(
                (before, after, datetime.utcnow())
            )

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        if reaction.message.guild:
            self.reaction_history.setdefault(reaction.message.channel.id, []).append(
                (reaction.message, reaction, user, datetime.utcnow())
            )

    @commands.command(
        name="clearsnipe",
        description="Clear all results for reactions, edits and messages",
    )
    @commands.has_permissions(manage_messages=True)
    async def clearsnipe(self, ctx):
        self.message_history.pop(ctx.channel.id, None)
        self.edit_history.pop(ctx.channel.id, None)
        self.reaction_history.pop(ctx.channel.id, None)
        await ctx.reply(
            embed=self.success_embed(description="cleared all sniped messages")
        )

    @commands.command(
        name="reactionsnipe", description="Snipe the latest reaction that was removed"
    )
    async def reactionsnipe(self, ctx):
        history = self.reaction_history.get(ctx.channel.id, [])
        if not history:
            return await ctx.reply(
                embed=self.warning_embed(
                    description="no recent reactions in this channel"
                )
            )

        message, reaction, user, timestamp = next(
            (m, r, u, t)
            for m, r, u, t in reversed(history)
            if datetime.utcnow() - t <= self.ttl
        )
        embed = discord.Embed(
            description=f"{user.mention} removed {
                reaction.emoji} from [this message]({message.jump_url})",
            url="https://discord.com",
            color=config.MAIN_COLOR,
        )
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.url)
        embed.timestamp = timestamp
        await ctx.reply(embed=embed)

    @commands.command(
        name="reactionhistory", description="See logged reactions for a message"
    )
    @commands.has_permissions(manage_messages=True)
    async def reactionhistory(self, ctx, message_link: str = None):
        try:
            if not message_link and ctx.message.reference:
                message_link = (
                    await ctx.fetch_message(ctx.message.reference.message_id)
                ).jump_url
            elif not message_link:
                return await ctx.reply(
                    embed=self.error_embed(description="no message provided")
                )

            channel_id, message_id = map(int, message_link.split("/")[-2:])
            channel = self.bot.get_channel(channel_id)
            message = await channel.fetch_message(message_id)

        except Exception:
            return await ctx.reply(
                embed=self.error_embed(description="invalid message link")
            )

        reactions = [
            (reaction, user, t)
            for m, reaction, user, t in self.reaction_history.get(channel.id, [])
            if m.id == message.id and datetime.utcnow() - t <= self.ttl
        ]

        if not reactions:
            return await ctx.reply(
                embed=self.warning_embed(
                    description="no recent reaction history for this message"
                )
            )

        grouped_reactions = {}
        for reaction, user, _ in reactions:
            if str(reaction.emoji) not in grouped_reactions:
                grouped_reactions[str(reaction.emoji)] = set()
            grouped_reactions[str(reaction.emoji)].add(user.mention)

        embed = discord.Embed(
            description=f"Message: {
                message.jump_url}",
            url="https://discord.com",
            color=config.MAIN_COLOR,
        )
        embed.set_author(name="Reaction history")
        for emoji, users in grouped_reactions.items():
            embed.add_field(name=emoji, value=", ".join(users), inline=True)
        await ctx.reply(embed=embed)

    @commands.command(
        name="editsnipe", description="Snipe the latest message that was edited"
    )
    async def editsnipe(self, ctx, index: int = 1):
        history = self.edit_history.get(ctx.channel.id, [])
        if not history:
            return await ctx.reply(
                embed=self.warning_embed(description="no recent edits in this channel")
            )

        valid_edits = [
            edit
            for edit in reversed(history)
            if datetime.utcnow() - edit[2] <= self.ttl
        ]

        if index < 1 or index > len(valid_edits):
            return await ctx.reply(
                embed=self.error_embed(
                    f"invalid index. there are {len(valid_edits)} recent edits"
                )
            )

        before, after, timestamp = valid_edits[index - 1]

        embed = discord.Embed(url="https://discord.com", color=config.MAIN_COLOR)

        inline = len(before.content) < 35 and len(after.content) < 35
        for text in (before.content, after.content):
            if len(text) > 253:
                text = text[:253] + "..."

        embed.add_field(name="Before", value=before.content or "Empty", inline=inline)
        embed.add_field(name="After", value=after.content or "Empty", inline=inline)
        embed.set_author(
            name=f"{before.author.display_name}",
            icon_url=before.author.display_avatar.url,
        )
        embed.set_footer(text=f"Edit {index} of {len(valid_edits)}")
        embed.timestamp = timestamp
        await ctx.reply(content=before.jump_url, embed=embed)

    @commands.command(
        name="snipe", description="Snipe the latest message that was deleted"
    )
    async def snipe(self, ctx, index: int = 1):
        history = self.message_history.get(ctx.channel.id, [])
        if not history:
            return await ctx.reply(
                embed=self.warning_embed(
                    description="no recent deletions in this channel"
                )
            )

        valid_deletions = [
            deletion
            for deletion in reversed(history)
            if datetime.utcnow() - deletion[1] <= self.ttl
        ]

        if index < 1 or index > len(valid_deletions):
            return await ctx.reply(
                embed=self.error_embed(
                    f"invalid index. there are {len(valid_deletions)} recent deletions"
                )
            )

        message, timestamp = valid_deletions[index - 1]

        embeds = await self.create_snipe_embed(
            message.content, message.author, message.attachments
        )

        if len(embeds) > 1:
            for i, embed in enumerate(embeds):
                if embed.image.url and ("tenor.com" in embed.image.url):
                    gif_url = await self.get_tenor_gif_url(embed.image.url)
                    embed.set_image(url=gif_url)

        for embed in embeds:
            embed.timestamp = timestamp
            embed.set_footer(text=f"{index} of {len(valid_deletions)}")

        await ctx.reply(embeds=embeds)


async def setup(bot):
    await bot.add_cog(Snipe(bot))
