import discord
from discord.ext import commands
import datetime
import platform
from urllib.parse import urlparse
import psutil
import os, sys
import re
import config
import timeago
from core.basecog import BaseCog
from collections import OrderedDict
import emojis


class Info(BaseCog):
    """quick info commands"""

    @commands.command(name="ping", brief="check the bot's latency")
    async def ping(self, ctx):
        """check the bot's latency"""

        start_time = datetime.datetime.utcnow()

        message = await ctx.reply(
            embed=self.embed(
                description=f"{config.WAIT_ICON} pinging...", color=config.WARN_COLOR
            )
        )

        end_time = datetime.datetime.utcnow()
        response_time = (end_time - start_time).total_seconds() * 1000
        heartbeat_latency = round(self.bot.latency * 1000)

        embed = self.embed(
            description=f"{config.SUCCESS_ICON} response time: `{response_time:.2f}ms`, bot latency: `{heartbeat_latency}ms`",
            color=config.SUCCESS_COLOR,
        )
        await message.edit(embed=embed)

    @commands.command(name="kys", brief="kill yourself")
    async def kys(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        await ctx.message.delete()
        await ctx.send(f"{user.mention} kys")

    @commands.command(name="avatar", brief="get an user's avatar", aliases=["av"])
    async def avatar(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        embed = self.embed()
        embed.set_author(name=f"{user.name}'s avatar", icon_url=user.display_avatar.url)
        embed.set_image(url=user.display_avatar.url)
        view = None
        if user.guild_avatar:

            class AvatarControls(discord.ui.View):
                def __init__(self, user):
                    self.selected = user.guild_avatar
                    super().__init__()

                    self.add_item(
                        discord.ui.Button(label="main avatar", custom_id="main")
                    )
                    self.add_item(
                        discord.ui.Button(
                            label="server avatar", custom_id="server", disabled=True
                        )
                    )

                    for child in self.children:
                        child.callback = self.button_callback

                async def button_callback(self, interaction: discord.Interaction):
                    button_id = interaction.data["custom_id"]

                    if interaction.user.id != ctx.author.id:
                        await interaction.response.send_message(
                            embed=self.error_embed(
                                "you cannot use these controls as you didn't invoke the command"
                            ),
                            ephemeral=True,
                        )
                        return

                    if button_id == "main":
                        self.selected = user.avatar
                        self.children[0].disabled = True
                        self.children[1].disabled = False

                    elif button_id == "server":
                        self.children[0].disabled = False
                        self.children[1].disabled = True
                        self.selected = user.guild_avatar

                    await interaction.response.edit_message(
                        embed=embed.set_image(url=self.selected.url), view=self
                    )

            view = AvatarControls(user)
        await ctx.reply(embed=embed, view=view)

    @commands.command(name="banner", brief="get an user's banner", aliases=["bn"])
    async def banner(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        user = await ctx.guild.fetch_member(user.id)
        view = None

        if not user.banner and not user.guild_banner:
            return await ctx.reply(
                embed=self.error_embed(
                    description="no banner set",
                )
            )

        embed = self.embed()
        embed.set_image(url=user.banner.url if user.banner else user.guild_banner.url)
        embed.set_author(name=f"{user.name}'s banner", icon_url=user.display_avatar.url)

        if user.guild_banner:

            class BannerControls(discord.ui.View):
                def __init__(self, user):
                    self.selected = user.guild_banner
                    super().__init__()

                    if user.banner:
                        self.add_item(
                            discord.ui.Button(label="main banner", custom_id="main")
                        )
                    self.add_item(
                        discord.ui.Button(
                            label="server banner", custom_id="server", disabled=True
                        )
                    )

                    for child in self.children:
                        child.callback = self.button_callback

                async def button_callback(self, interaction: discord.Interaction):
                    button_id = interaction.data["custom_id"]

                    if interaction.user.id != ctx.author.id:
                        await interaction.response.send_message(
                            embed=self.error_embed(
                                "you cannot use these controls as you didn't invoke the command"
                            ),
                            ephemeral=True,
                        )
                        return

                    if button_id == "main":
                        self.selected = user.banner
                        self.children[0].disabled = True
                        self.children[1].disabled = False

                    elif button_id == "server":
                        self.selected = user.guild_banner
                        self.children[0].disabled = False
                        self.children[1].disabled = True

                    await interaction.response.edit_message(
                        embed=embed.set_image(url=self.selected.url), view=self
                    )

            view = BannerControls(user)
        await ctx.reply(embed=embed, view=view)

    @commands.command(
        name="guildavatar",
        brief="get a guild's avatar",
        aliases=["gavatar", "gav", "gicon", "serveravatar", "sav", "sicon"],
    )
    async def guildavatar(self, ctx):
        if not ctx.guild.icon:
            return await ctx.reply(
                embed=self.error_embed(
                    description="no icon set",
                )
            )

        embed = self.embed(description=f"**{ctx.guild.name}**'s icon")
        embed.set_image(url=ctx.guild.icon.url)
        await ctx.reply(embed=embed)

    @commands.command(
        name="guildbanner",
        brief="get a guild's banner",
        aliases=["gbanner", "gbn", "serverbanner", "sbanner", "sbn"],
    )
    async def guildbanner(self, ctx):
        if not ctx.guild.banner:
            return await ctx.reply(
                embed=self.error_embed(
                    description="no banner set",
                )
            )

        embed = self.embed(description=f"**{ctx.guild.name}**'s banner")
        embed.set_image(url=ctx.guild.banner.url)
        await ctx.reply(embed=embed)

    @commands.command(name="splash", brief="view the server splash image")
    async def splash(self, ctx):
        """view the server splash image"""
        if not ctx.guild.splash:
            return await ctx.reply(
                embed=self.error_embed(
                    description="no splash set",
                )
            )
        await ctx.reply(
            embed=self.embed(description=f"**{ctx.guild.name}**'s splash").set_image(
                url=ctx.guild.splash.url
            )
        )

    @commands.command(
        name="boosters", brief="view all server boosters", aliases=["boost", "boosts"]
    )
    async def boosters(self, ctx):
        """view all server boosters"""
        boosters = [i for i in ctx.guild.premium_subscribers]
        if not boosters:
            return await ctx.reply(
                embed=self.warning_embed(
                    description="no boosters found",
                )
            )

        boosters_per_page = 10
        pages = []
        for i in range(0, len(boosters), boosters_per_page):
            page = boosters[i : i + boosters_per_page]
            pages.append(
                self.embed(
                    description="\n".join(
                        f"- {booster.mention} since **{discord.utils.format_dt(booster.premium_since, style='R')}**"
                        for booster in page
                    )
                )
                .set_thumbnail(url=ctx.guild.icon.url)
                .set_author(name=f"{ctx.guild.name}'s boosters")
            )
        await self.paginate(ctx, pages)

    @commands.command(name="bots", brief="view all bots in the server")
    async def bots(self, ctx):
        """view all bots in the server"""
        bots = [i for i in ctx.guild.members if i.bot]
        if not bots:
            return await ctx.reply(
                embed=self.warning_embed(
                    description="no bots found",
                )
            )

        bots_per_page = 10
        pages = []
        for i in range(0, len(bots), bots_per_page):
            page = bots[i : i + bots_per_page]
            pages.append(
                self.embed(
                    description="\n".join(f"- {bot.mention} `{bot.id}`" for bot in page)
                )
                .set_thumbnail(url=ctx.guild.icon.url)
                .set_author(name=f"{ctx.guild.name}'s bots")
            )
        await self.paginate(ctx, pages)

    @commands.command(name="channelinfo", brief="get info about a channel")
    async def channelinfo(self, ctx, channel: discord.TextChannel = None):
        """get info about a channel"""
        channel = channel or ctx.channel
        embed = self.embed(title=f"{channel.mention}")
        embed.add_field(
            name="name",
            value=channel.name,
            inline=True,
        )
        embed.add_field(
            name="id",
            value=channel.id,
            inline=True,
        )
        embed.add_field(
            name="type",
            value=channel.type.name.lower(),
            inline=True,
        )

        await ctx.reply(embed=embed)

    @commands.group(name="emoji", brief="manage emojis", invoke_without_subcommand=True)
    async def emoji(self, ctx):
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @commands.command(name="userinfo", brief="get info about a user", aliases=["ui"])
    async def userinfo(self, ctx, user: discord.Member = None):
        user = user or ctx.author
        global_user = await self.bot.fetch_user(user.id)
        embed = self.embed(description=f"id: `{user.id}`", color=user.color)
        embed.set_author(name=f"{user.name}'s info", icon_url=user.avatar.url)
        embed.add_field(
            name="created at",
            value=f"<t:{int(user.created_at.timestamp())}:D> | **{timeago.format(user.created_at.replace(tzinfo=None), datetime.datetime.utcnow())}**",
            inline=False,
        )
        embed.add_field(
            name="joined at",
            value=f"<t:{int(user.joined_at.timestamp())}:D> | **{timeago.format(user.joined_at.replace(tzinfo=None), datetime.datetime.utcnow())}**",
            inline=False,
        )
        embed.set_thumbnail(url=user.avatar.url)
        if global_user.banner:
            embed.set_image(url=global_user.banner.url)
        await ctx.reply(embed=embed)

    @commands.command(
        name="serverinfo", brief="get info about a server", aliases=["si"]
    )
    async def serverinfo(self, ctx):
        """get info about a server"""
        guild = ctx.guild

        banner = f"[URL]({guild.banner.url})" if guild.banner else "Unset"
        splash = f"[URL]({guild.splash.url})" if guild.splash else "Unset"
        icon = f"[URL]({guild.icon.url})" if guild.icon else "Unset"

        embed = self.embed(
            description=f"id: `{guild.id}`\n{guild.description}", color=guild.me.color
        )
        embed.set_author(name=f"{guild.name}'s info", icon_url=guild.icon.url)
        embed.add_field(
            name="Created at",
            value=f"<t:{int(guild.created_at.timestamp())}:D> | **{timeago.format(guild.created_at.replace(tzinfo=None), datetime.datetime.utcnow())}**",
            inline=False,
        )
        embed.add_field(
            name="Owner",
            value=f"{guild.owner.mention}",
            inline=True,
        )
        embed.add_field(
            name=f"Members: **{guild.member_count}**",
            value=f"├ bots: **{len([i for i in guild.members if i.bot])}**\n└ users: **{len([i for i in guild.members if not i.bot])}**",
            inline=True,
        )
        embed.add_field(
            name="Info",
            value=f"├ Verification: **{guild.verification_level}**\n├ Boosts: **{guild.premium_subscription_count}**\n└ Level **{guild.premium_tier}**",
        )
        embed.add_field(
            name=f"Channels: **{len(guild.channels)}**",
            value=f"├ Categories: **{len([i for i in guild.categories])}**\n├ Text: **{len([i for i in guild.text_channels])}**\n└ Voice: **{len([i for i in guild.voice_channels])}**",
        )
        embed.add_field(
            name="Stats",
            value=f"├ Roles: **{len(guild.roles)}**\n├ Emojis: **{len(guild.emojis)}**\n└ Boosters: **{len([i for i in guild.premium_subscribers])}**",
        )
        embed.add_field(
            name="Assets",
            value=f"├ Icon: **{icon}**\n├ Banner: **{banner}**\n└ Splash: **{splash}**",
        )
        embed.set_thumbnail(url=guild.icon.url)
        await ctx.reply(embed=embed)

    @emoji.command(name="add", brief="add an emoji to the server")
    @commands.has_permissions(manage_emojis=True)
    async def emoji_add(self, ctx, emoji_source: str = None, name: str = None):
        await ctx.message.add_reaction(config.THINK_ICON)
        if ctx.message.attachments:
            image = ctx.message.attachments[0]
            emoji_img = await image.read()

            if emoji_source and not self.is_image_or_emoji(emoji_source):
                emoji_name = emoji_source
            else:
                emoji_name = name or image.filename.split(".")[0]

        elif emoji_source:
            if emoji_source.startswith("<"):
                emoji = discord.PartialEmoji.from_str(emoji_source)
                async with ctx.bot.session.get(emoji.url) as resp:
                    emoji_img = await resp.read()
                emoji_name = name or emoji.name

            else:
                parsed_url = urlparse(emoji_source)
                if not all([parsed_url.scheme, parsed_url.netloc]):
                    await ctx.reply(
                        embed=self.error_embed(
                            description="provide a valid image / URL"
                        )
                    )
                    return await ctx.message.remove_reaction(
                        config.THINK_ICON, self.bot.user
                    )

                async with ctx.bot.session.get(emoji_source) as resp:
                    if resp.status != 200:
                        await ctx.reply(
                            embed=self.error_embed(
                                description="could not download the image"
                            )
                        )
                        return await ctx.message.remove_reaction(
                            config.THINK_ICON, self.bot.user
                        )
                    emoji_img = await resp.read()

                emoji_name = (
                    name or urlparse(emoji_source).path.split("/")[-1].split(".")[0]
                )

        else:
            await ctx.reply(
                embed=self.error_embed(
                    description="please provide an image / URL / emoji"
                ),
            )
            return await ctx.message.remove_reaction(config.THINK_ICON, self.bot.user)

        emoji_name = "".join(c for c in emoji_name if c.isalnum())

        try:
            emoji = await ctx.guild.create_custom_emoji(
                name=emoji_name, image=emoji_img
            )
            await ctx.reply(
                embed=self.success_embed(description=f"emoji added: {emoji}")
            )
        except discord.HTTPException as e:
            if e.code == 308:
                await ctx.reply(
                    embed=self.error_embed(
                        description="server has reached the maximum number of emojis"
                    )
                )
            elif e.code == 400:
                await ctx.reply(
                    embed=self.error_embed(description="invalid image or emoji name")
                )
            else:
                await ctx.reply(
                    embed=self.error_embed(description="failed to add emoji")
                )

        await ctx.message.remove_reaction(config.THINK_ICON, self.bot.user)

    def is_image_or_emoji(self, text):
        """
        Check if the input is a URL or an emoji
        """
        if text.startswith("<"):
            return True

        try:
            parsed_url = urlparse(text)
            return all([parsed_url.scheme, parsed_url.netloc])
        except:
            return False

    @emoji.command(
        name="remove", brief="remove an emoji from the server", aliases=["rm"]
    )
    @commands.has_permissions(manage_emojis=True)
    async def emoji_remove(self, ctx, emoji: str):
        try:
            emoji = discord.utils.get(ctx.guild.emojis, name=emoji.split(":")[1])
        except:
            return await ctx.reply(
                embed=self.error_embed(description="emoji appears invalid")
            )
        if emoji and emoji.guild.id == ctx.guild.id:
            await emoji.delete()
            return await ctx.reply(
                embed=self.success_embed(description=f"emoji removed: **{emoji.name}**")
            )
        await ctx.reply(
            embed=self.error_embed(description="this emoji is not from this server")
        )

    @emoji.command(name="info", brief="view info about an emoji")
    async def emoji_info(self, ctx, *, emoji_input: str = None):
        """Gets information about a given emoji."""
        pages = []
        emoji_list = []

        if ctx.message.reference:
            replied_msg = await ctx.channel.fetch_message(
                ctx.message.reference.message_id
            )
            emoji_list = list(
                OrderedDict.fromkeys(
                    char
                    for char in replied_msg.content.split(" ")
                    if char in replied_msg.clean_content.split(" ")
                    and (
                        (char.startswith("<") and char.endswith(">"))
                        or (emojis.count(char) > 0)
                    )
                )
            )

        if emoji_input:
            emoji_list.append(emoji_input)

        for emoji in emoji_list:
            embed = discord.Embed(color=config.MAIN_COLOR)

            if emoji.startswith("<"):
                match = discord.utils.get(ctx.guild.emojis, name=emoji.split(":")[1])
                embed.set_author(name="custom emoji")
                embed.description = f"id: `{match.id}`"
                embed.add_field(name="name", value=match.name, inline=True)
                embed.add_field(name="url", value=f"[click me]({match.url})")
                embed.add_field(
                    name="animated", value="yes" if match.animated else "no"
                )
                embed.add_field(
                    name="created at",
                    value=f"<t:{int(match.created_at.timestamp())}:D> | **{timeago.format(match.created_at.replace(tzinfo=None), datetime.datetime.utcnow())}**",
                    inline=False,
                )
                embed.set_thumbnail(url=match.url)
            else:
                emoji_data = await self.fetch_default_emoji_info(emoji)
                if emoji_data:
                    embed.title = f"{emoji_data.get('annotation', 'unknown')}"
                    embed.set_author(name="default emoji")
                    embed.add_field(
                        name="unicode", value=f"`U+{ord(emoji):X}`", inline=True
                    )
                    embed.add_field(
                        name="category",
                        value=emoji_data.get("group", "N/A"),
                        inline=True,
                    )
                    embed.set_thumbnail(
                        url=f"https://www.emoji.family/api/emojis/{emoji}/twemoji/png/64"
                    )
                else:
                    embed.description = f"could not find emoji **{emoji}**"

            pages.append(embed)

        await self.paginate(ctx, pages, compact=True)

    async def fetch_default_emoji_info(self, emoji):
        async with self.bot.session.get(
            f"https://www.emoji.family/api/emojis/{emoji}"
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            return None

    @commands.command(name="define", brief="fetch definition for a given word")
    async def define(self, ctx, *, word):
        """
        Fetch definition for a given word

        Parameters:
        - word: The word to look up
        """
        dictionary_api = "https://api.dictionaryapi.dev/api/v2/entries/en/{}"
        async with self.bot.session.get(dictionary_api.format(word)) as response:
            if response.status != 200:
                await ctx.reply(
                    embed=self.error_embed(
                        description=f"could not find definition for **{word}**"
                    )
                )
                return

            try:
                data = await response.json()

                if not data:
                    await ctx.reply(
                        embed=self.error_embed(
                            description=f"no definitions found for **{word}**"
                        )
                    )
                    return

                entry = data[0]

                phonetic = self._extract_phonetic(entry.get("phonetics", []))

                pages = []
                for meaning in entry.get("meanings", []):
                    part_of_speech = meaning.get("partOfSpeech", "unknown")

                    for definition in meaning.get("definitions", []):
                        def_text = definition.get(
                            "definition", "no definition available."
                        )
                        embed = discord.Embed(
                            title=entry.get("word", word).capitalize(),
                            description=def_text,
                            color=config.MAIN_COLOR,
                        )

                        if phonetic:
                            embed.set_author(name=f"{phonetic} ({part_of_speech})")

                        example = definition.get("example", "no example available")
                        embed.add_field(name="example", value=example, inline=True)

                        antonyms = definition.get("antonyms", [])
                        antonyms_text = (
                            ", ".join(antonyms) if antonyms else "no antonyms available"
                        )
                        embed.add_field(
                            name="antonyms", value=antonyms_text, inline=True
                        )

                        pages.append(embed)

                await self.paginate(ctx, pages, compact=True)

            except Exception as e:
                return await ctx.reply(
                    embed=self.error_embed(description="failed to get definition")
                )

    def _extract_phonetic(self, phonetics):
        """
        Extract phonetic text, handling various possible structures

        Parameters:
        - phonetics: List of phonetic entries

        Returns:
        - Phonetic text or empty string
        """
        for entry in phonetics:
            if entry.get("text"):
                return entry["text"]

        return ""

    @commands.command(
        name="hasrole", brief="shows users with a role", aliases=["inrole"]
    )
    @commands.has_permissions(manage_roles=True)
    async def hasrole(self, ctx, role: discord.Role):
        """shows users with a role"""
        users = [user for user in ctx.guild.members if role in user.roles]
        if not users:
            return await ctx.reply(
                embed=self.error_embed(
                    description=f"no users with the role {role.name}",
                )
            )
        await ctx.reply(
            embed=self.embed(
                description=" ".join([user.mention for user in users]),
            ).set_author(name=f"users for @{role.name}")
        )

    @commands.command(
        name="membercount", brief="shows member count", aliases=["members", "mc"]
    )
    async def membercount(self, ctx):
        """shows member count"""
        embed = self.embed(
            description=f"this guild has **{ctx.guild.member_count:,}** members",
        )
        embed.add_field(
            name="users", value=f"{len([i for i in ctx.guild.members if not i.bot]):,}"
        )
        embed.add_field(
            name="bots", value=f"{len([i for i in ctx.guild.members if i.bot]):,}"
        )
        embed.set_thumbnail(url=ctx.guild.icon.url)
        await ctx.reply(embed=embed)

    @commands.command(name="roleinfo", brief="get info about a role")
    @commands.has_permissions(manage_roles=True)
    async def roleinfo(self, ctx, role: discord.Role):
        embed = self.embed(description=f"id: `{role.id}`", color=role.color)
        icon = None
        if role.unicode_emoji:
            icon = f"https://www.emoji.family/api/emojis/{role.unicode_emoji}/twemoji/png/64"
        elif role.display_icon:
            icon = role.display_icon.url
        else:
            icon = f"https://singlecolorimage.com/get/{'%02x%02x%02x' % role.color.to_rgb()}/32x32"

        embed.set_author(name=f"@{role.name}", icon_url=icon)
        embed.add_field(name="color", value="`#%02x%02x%02x`" % role.color.to_rgb())
        embed.add_field(name="position", value=role.position)
        embed.add_field(
            name="users",
            value=f"{len([i for i in ctx.guild.members if role in i.roles])} total",
        )
        embed.add_field(
            name="created at",
            value=f"<t:{int(role.created_at.timestamp())}:D> | **{timeago.format(role.created_at.replace(tzinfo=None), datetime.datetime.utcnow())}**",
        )
        await ctx.reply(embed=embed)


async def setup(bot):
    await bot.add_cog(Info(bot))
