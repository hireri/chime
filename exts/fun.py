import asyncio
import os
import random
import traceback
from itertools import islice
from urllib.parse import urlparse

import discord
import dotenv
import duckduckgo_images_api
import googlesearch
from discord.ext import commands
from groq import AsyncGroq

import config
from core.basecog import BaseCog
from core.database import db

dotenv.load_dotenv()


class Fun(BaseCog):
    def __init__(self, bot):
        self.tags_blocked = []
        super().__init__(bot)

    def gen(self, generator, group_size=3):
        while True:
            group = list(islice(generator, group_size))

            if not group:
                break

            yield group

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.tags_blocked:
            tag_group = self.bot.get_command("tag")
            self.tags_blocked = (
                [
                    name_or_alias
                    for subcommand in tag_group.commands
                    for name_or_alias in [subcommand.name] + subcommand.aliases
                ]
                if isinstance(tag_group, commands.Group)
                else []
            )

    async def search(self, query):
        results = await asyncio.to_thread(
            googlesearch.search,
            query,
            num_results=30,
            lang="en",
            advanced=True,
            safe="active",
            unique=True,
        )

        embeds = []

        for triplet in self.gen(results, 3):
            embed = self.embed()
            embed.set_author(
                name=f"search results for {query}",
                icon_url=self.bot.application_emojis.get(
                    int(config.GOOGLE_ICON.split(":")[2][:-1])
                ).url,
            )
            for i in triplet:
                if not i.url:
                    continue

                embed.add_field(
                    name=f"{config.SEARCH_ICON} {i.title or query}",
                    value=f"[{urlparse(i.url).netloc}]({i.url})\n{i.description or '*no description*'}",
                    inline=False,
                )
            embeds.append(embed)

        return embeds

    async def image_search(self, query):
        results = await asyncio.to_thread(
            duckduckgo_images_api.search,
            query,
        )
        print(results)
        embeds = []
        for result in results["results"]:
            embed = self.embed(description=f"[source]({result['url']})")
            embed.set_author(
                name=f"image results for {query}",
                icon_url=self.bot.application_emojis.get(
                    int(config.SEARCH_ICON.split(":")[2][:-1])
                ).url,
            )
            embed.set_image(url=result["image"])
            embeds.append(embed)
        return embeds

    @commands.command(name="google", brief="search Google for a query")
    async def google(self, ctx, *, query):
        results = await self.search(query)

        if results:
            return await self.paginate(ctx, results)

        await ctx.reply(embed=self.error_embed(description="no results found"))

    @commands.command(name="image", brief="search for an image")
    async def image(self, ctx, *, query):
        await ctx.message.add_reaction(config.THINK_ICON)
        try:
            results = await self.image_search(query)
            await self.paginate(ctx, results)
        except Exception:
            await ctx.reply(embed=self.error_embed(description="no results found"))
        await ctx.message.remove_reaction(config.THINK_ICON, self.bot.user)

    @commands.command(name="ai", brief="talk to ai")
    async def ai(self, ctx, *, query):
        await ctx.message.add_reaction(config.THINK_ICON)
        try:
            client = AsyncGroq(api_key=os.getenv("AI_KEY"))
            messages = [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": query}],
                }
            ]
            if ctx.message.attachments and ctx.message.attachments[
                0
            ].content_type.startswith("image/"):
                messages[0]["content"].append(
                    {
                        "type": "image_url",
                        "image_url": {"url": ctx.message.attachments[0].url},
                    }
                )
            response = await client.chat.completions.create(
                model="llama-3.2-11b-vision-preview",
                messages=messages,
                max_completion_tokens=250,
            )
            await ctx.reply(
                embed=self.embed(
                    description=response.choices[0].message.content
                ).set_author(
                    name="llama 3.2 11b vision preview",
                    icon_url="https://images.seeklogo.com/logo-png/59/1/ollama-logo-png_seeklogo-593420.png",
                )
            )
        except Exception:
            print(traceback.format_exc())
            await ctx.reply(embed=self.error_embed(description="the ai didn't respond"))
        await ctx.message.remove_reaction(config.THINK_ICON, self.bot.user)

    @commands.group(name="tag", aliases=["tags"], invoke_without_command=True)
    async def tag(self, ctx, tag_name: str):
        """get a tag by its name"""
        tag = await db.get_tag(guild_id=ctx.guild.id, name=tag_name)

        if tag:
            await db.use_tag(tag["id"])
            await ctx.reply(tag["content"])
        else:
            await ctx.reply(embed=self.error_embed(description="tag not found"))

    @tag.command(name="create", aliases=["new", "add", "update"])
    async def create_tag(self, ctx, tag_name: str, *, description: str):
        """create or update a tag"""
        if tag_name in self.tags_blocked:
            return await ctx.reply(
                embed=self.error_embed(description="invalid tag name")
            )

        tag = await db.get_tag(name=tag_name, guild_id=ctx.guild.id)

        if tag:
            if tag["user_id"] != ctx.author.id:
                await ctx.reply(
                    self.warning_embed(description=f"tag **{tag_name}** already exists")
                )
                return
            else:
                await db.update_tag(tag, name=tag_name, content=description)
                await ctx.reply(
                    self.success_embed(description=f"tag **{tag_name}** updated")
                )
        else:
            tag = await db.create_tag(
                name=tag_name,
                content=description,
                user_id=ctx.author.id,
                guild_id=ctx.guild.id,
            )
            await ctx.reply(
                embed=self.success_embed(description=f"tag {tag_name} created")
            )

    @tag.command(name="delete", aliases=["remove", "del", "rm"])
    async def delete_tag(self, ctx, tag_name: str):
        """delete a tag if it belongs to the user"""
        tag = await db.get_tag(name=tag_name, guild_id=ctx.guild.id)
        if tag:
            if tag["user_id"] != ctx.author.id:
                await ctx.reply(
                    embed=self.warning_embed(
                        description=f"tag **{tag_name}** does not belong to you"
                    )
                )
                return
            else:
                await db.delete_tag(tag["id"])
                await ctx.reply(
                    embed=self.success_embed(description=f"tag **{tag_name}** deleted")
                )
        else:
            await ctx.reply(
                embed=self.error_embed(description=f"tag **{tag_name}** does not exist")
            )

    @tag.command(name="list")
    async def list_tags(self, ctx, user: discord.Member | str | None = None):
        """list all tags"""
        tags = await db.get_tags(guild_id=ctx.guild.id)
        name = f"tags in {ctx.guild.name}"
        icon_url = ctx.guild.icon.url
        if user:
            tags = [tag for tag in tags if tag["user_id"] == user.id]
            name = f"tags by {user.name}"
            icon_url = user.display_avatar.url
        if not tags:
            await ctx.reply(embed=self.error_embed(description="no tags found"))
        else:
            tags_per_page = 10
            pages = []
            for i in range(0, len(tags), tags_per_page):
                page = tags[i : i + tags_per_page]
                pages.append(
                    self.embed(
                        description="\n".join(
                            f"- **{tag['name']}** by <@{tag['user_id']}>"
                            for tag in page
                        )
                    ).set_author(name=name, icon_url=icon_url)
                )
            await self.paginate(ctx, pages)

    @tag.command(name="info")
    async def tag_info(self, ctx, tag_name: str):
        """get information about a tag"""
        tag = await db.get_tag(name=tag_name, guild_id=ctx.guild.id)
        if tag:
            embed = discord.Embed(
                description=f"info for `{tag_name}`.",
                color=config.MAIN_COLOR,
            )
            tag_content = (
                tag["content"]
                if len(tag["content"]) < 1024
                else tag["content"][:1024] + "..."
            )
            embed.add_field(name="tag contents", value=tag_content, inline=False)
            embed.add_field(
                name="created at",
                value=discord.utils.format_dt(tag["created_at"], style="R"),
                inline=True,
            )
            embed.add_field(
                name="created by", value=f"<@{tag['user_id']}>", inline=True
            )
            embed.add_field(name="uses", value=f"{tag['uses']}", inline=True)
            await ctx.reply(embed=embed)

        else:
            await ctx.reply(
                embed=self.error_embed(
                    description=f"tag {tag_name} not found",
                )
            )

    @tag.command(name="rename", aliases=["rn"])
    async def rename_tag(self, ctx, old_name: str, new_name: str):
        """rename a tag"""
        if new_name in ["create", "new", "delete", "remove", "del", "list", "info"]:
            return await ctx.reply(
                embed=self.error_embed(description="invalid tag name")
            )

        tag = await self.get_tag(ctx, name=old_name, guild_id=ctx.guild.id)
        if not tag:
            return await ctx.reply(embed=self.error_embed(description="tag not found"))

        await db.update_tag(tag, name=new_name)
        await ctx.reply(
            embed=self.success_embed(
                description=f"tag **{old_name}** renamed to **{new_name}**"
            )
        )

    @tag.command(name="reset", aliases=["deleteall", "delall", "rmall"])
    @commands.has_permissions(manage_guild=True)
    async def reset_tags(self, ctx):
        """delete all tags"""
        tags = await db.get_tags(guild_id=ctx.guild.id)
        if not tags:
            return await ctx.reply(embed=self.error_embed(description="no tags found"))

        await db.reset_tags(guild_id=ctx.guild.id)
        await ctx.reply(embed=self.success_embed(description="all tags deleted"))

    @tag.command(name="random", aliases=["rand"])
    async def random_tag(self, ctx):
        """get a random tag"""
        tags = await db.get_tags(guild_id=ctx.guild.id)
        if not tags:
            return await ctx.reply(embed=self.error_embed(description="no tags found"))

        tag = random.choice(tags)
        await db.use_tag(tag["id"])
        await ctx.reply(f"**{tag['name']}**\n> {tag['content']}")

    @tag.command(name="search", aliases=["find"])
    async def search_tag(self, ctx, *, query):
        """search for a tag"""
        tags = await db.get_tags(guild_id=ctx.guild.id)
        if not tags:
            return await ctx.reply(embed=self.error_embed(description="no tags found"))

        tag_list = [tag for tag in tags if query in tag["name"].lower()]
        if not tag_list:
            return await ctx.reply(embed=self.error_embed(description="tag not found"))

        tags_per_page = 10
        pages = []
        for i in range(0, len(tag_list), tags_per_page):
            page = tag_list[i : i + tags_per_page]
            pages.append(
                self.embed(
                    description="\n".join(
                        f"- **{tag['name']}** by <@{tag['user_id']}>" for tag in page
                    )
                ).set_author(
                    name=f"search results for {query}", icon_url=ctx.guild.icon.url
                )
            )

        await self.paginate(ctx, pages)

    @commands.command(name="urban", brief="get a random urban dictionary definition")
    async def urban(self, ctx, *, query):
        """get a random urban dictionary definition"""
        async with self.bot.session.get(
            f"https://api.urbandictionary.com/v0/define?term={query}"
        ) as resp:
            if resp.status != 200:
                await ctx.reply(
                    embed=self.error_embed(description="could not get definition")
                )
                return
            data = await resp.json()
            pages = []
            for definition in data["list"]:
                page = self.embed(
                    description=definition["definition"],
                    color=config.MAIN_COLOR,
                )
                if definition["example"]:
                    page.add_field(name="example", value=definition["example"])
                if definition["author"]:
                    page.set_footer(
                        text=f"by {definition['author']}, {definition['thumbs_up']} likes",
                    )
                if definition["permalink"]:
                    page.set_author(
                        name=definition["word"],
                        url=definition["permalink"],
                        icon_url="https://media.licdn.com/dms/image/v2/D560BAQGlykJwWd7v-g/company-logo_200_200/company-logo_200_200/0/1718946315384/urbandictionary_logo?e=2147483647&v=beta&t=jnPuu32SKBWZsFOfOHz7KugJq0S2UARN8CL0wOAyyro",
                    )
                pages.append(page)
            await self.paginate(ctx, pages)


async def setup(bot):
    await bot.add_cog(Fun(bot))
