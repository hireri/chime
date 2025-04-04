import asyncio
import os
import io
import random
from itertools import islice
from urllib.parse import urlparse

import discord
import dotenv
import duckduckgo_images_api
import googlesearch
from discord.ext import commands
from discord import ui, File
from groq import AsyncGroq

import config
from core.basecog import BaseCog
from core.database import db

dotenv.load_dotenv()


class ReplyModal(ui.Modal):
    def __init__(self, title, history):
        super().__init__(title=title)
        self.history = history
        self.user_input = ui.TextInput(
            label="Your message",
            placeholder="Enter your message here...",
            style=discord.TextStyle.paragraph,
            max_length=2000,
        )
        self.add_item(self.user_input)

    async def on_submit(self, interaction: discord.Interaction):
        del_resp = await interaction.response.defer(thinking=True)

        self.history.append({"role": "user", "content": self.user_input.value})

        model = "llama-3.2-90b-vision-preview"

        messages = []
        for entry in self.history:
            if entry["role"] == "user":
                messages.append(
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": entry["content"]}],
                    }
                )
            else:
                messages.append({"role": "assistant", "content": entry["content"]})

        try:
            client = AsyncGroq(api_key=os.getenv("AI_KEY"))
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_completion_tokens=1024,
            )

            response_text = response.choices[0].message.content

            self.history.append({"role": "assistant", "content": response_text})

            words_per_page = 148
            pages = []
            for i in range(0, len(response_text.split(" ")), words_per_page):
                page = response_text.split(" ")[i : i + words_per_page]
                pages.append(
                    self.cog.embed(description=" ".join(page)).set_author(
                        name=" ".join(model.split("-")),
                        icon_url="https://images.seeklogo.com/logo-png/59/1/ollama-logo-png_seeklogo-593420.png",
                    )
                )

            reply_button = ui.Button(
                emoji=config.PLANE_ICON, style=discord.ButtonStyle.gray
            )

            async def new_reply_callback(new_interaction: discord.Interaction):
                if new_interaction.user.id != self.ctx.author.id:
                    await new_interaction.response.send_message(
                        embed=self.cog.error_embed(
                            description="you cannot use these controls"
                        ),
                        ephemeral=True,
                    )
                    return

                new_modal = ReplyModal(
                    title="Continue conversation", history=self.history
                )
                new_modal.cog = self.cog
                new_modal.ctx = self.ctx

                await new_interaction.response.send_modal(new_modal)

            reply_button.callback = new_reply_callback

            download_button = ui.Button(
                emoji=config.DOWNLOAD_ICON, style=discord.ButtonStyle.gray
            )

            async def download_callback(new_interaction: discord.Interaction):
                file = io.BytesIO(response_text.encode())
                await new_interaction.response.send_message(
                    file=File(file, filename="response.txt"), ephemeral=True
                )

            download_button.callback = download_callback

            await del_resp.resource.delete()
            await self.cog.paginate(
                self.ctx,
                pages,
                compact=True,
                extra_buttons=[reply_button, download_button],
            )

        except Exception as e:
            print(e)
            await self.ctx.channel.send(
                embed=self.cog.error_embed(description="the ai didn't respond")
            )


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
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def google(self, ctx, *, query):
        results = await self.search(query)

        if results:
            return await self.paginate(ctx, results)

        await ctx.reply(embed=self.error_embed(description="no results found"))

    @commands.command(name="image", brief="search for an image")
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def image(self, ctx, *, query):
        await ctx.message.add_reaction(config.THINK_ICON)
        try:
            results = await self.image_search(query)
            await self.paginate(ctx, results)
        except Exception:
            await ctx.reply(embed=self.error_embed(description="no results found"))
        await ctx.message.remove_reaction(config.THINK_ICON, self.bot.user)

    async def ai_gen(
        self,
        message,
        history,
        model,
        query=None,
    ) -> str:
        client = AsyncGroq(api_key=os.getenv("AI_KEY"))
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": message.content if not query else query}
                ],
            }
        ]
        if message.attachments and message.attachments[0].content_type.startswith(
            "image/"
        ):
            messages[0]["content"].append(
                {
                    "type": "image_url",
                    "image_url": {"url": message.attachments[0].url},
                }
            )

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_completion_tokens=1024,
        )

        return response.choices[0].message.content, history

    @commands.command(name="ai", brief="talk to ai")
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def ai(self, ctx, *, query):
        await ctx.message.add_reaction(config.THINK_ICON)
        try:
            model = "llama-3.2-90b-vision-preview"

            history = [{"role": "user", "content": query}]
            response_text, _ = await self.ai_gen(ctx.message, {}, model, query=query)
            history.append({"role": "assistant", "content": response_text})

            words_per_page = 148
            pages = []
            for i in range(0, len(response_text.split(" ")), words_per_page):
                page = response_text.split(" ")[i : i + words_per_page]
                pages.append(
                    self.embed(description=" ".join(page)).set_author(
                        name=" ".join(model.split("-")),
                        icon_url="https://images.seeklogo.com/logo-png/59/1/ollama-logo-png_seeklogo-593420.png",
                    )
                )

            reply_button = ui.Button(
                emoji=config.PLANE_ICON, style=discord.ButtonStyle.gray
            )

            async def reply_callback(interaction: discord.Interaction):
                if interaction.user.id != ctx.author.id:
                    await interaction.response.send_message(
                        embed=self.error_embed(
                            description="you cannot use these controls"
                        ),
                        ephemeral=True,
                    )
                    return

                modal = ReplyModal(title="Continue conversation", history=history)
                modal.cog = self
                modal.ctx = ctx

                await interaction.response.send_modal(modal)

            reply_button.callback = reply_callback

            download_button = ui.Button(
                emoji=config.DOWNLOAD_ICON, style=discord.ButtonStyle.gray
            )

            async def download_callback(interaction: discord.Interaction):
                file = io.BytesIO(response_text.encode())
                await interaction.response.send_message(
                    file=File(file, filename="response.txt"), ephemeral=True
                )

            download_button.callback = download_callback

            await self.paginate(
                ctx, pages, compact=True, extra_buttons=[reply_button, download_button]
            )

        except Exception as e:
            print(e)
            await ctx.reply(embed=self.error_embed(description="the ai didn't respond"))
        finally:
            await ctx.message.remove_reaction(config.THINK_ICON, self.bot.user)

    @commands.group(name="tag", aliases=["tags"], invoke_without_command=True)
    @commands.cooldown(3, 5, commands.BucketType.user)
    async def tag(self, ctx, tag_name: str):
        """get a tag by its name"""
        tag = await db.get_tag(guild_id=ctx.guild.id, name=tag_name)

        if tag:
            await db.use_tag(tag["id"])
            await ctx.reply(tag["content"])
        else:
            await ctx.reply(embed=self.error_embed(description="tag not found"))

    @tag.command(name="create", aliases=["new", "add", "update"])
    @commands.cooldown(1, 15, commands.BucketType.user)
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
                    embed=self.warning_embed(
                        description=f"tag **{tag_name}** already exists"
                    )
                )
                return
            else:
                await db.update_tag(tag, name=tag_name, content=description)
                await ctx.reply(
                    embed=self.success_embed(description=f"tag **{tag_name}** updated")
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
    @commands.cooldown(1, 10, commands.BucketType.user)
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
    @commands.cooldown(1, 5, commands.BucketType.user)
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
    @commands.cooldown(3, 5, commands.BucketType.user)
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
    @commands.cooldown(1, 10, commands.BucketType.user)
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
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def reset_tags(self, ctx):
        """delete all tags"""
        tags = await db.get_tags(guild_id=ctx.guild.id)
        if not tags:
            return await ctx.reply(embed=self.error_embed(description="no tags found"))

        await db.reset_tags(guild_id=ctx.guild.id)
        await ctx.reply(embed=self.success_embed(description="all tags deleted"))

    @tag.command(name="random", aliases=["rand"])
    @commands.cooldown(3, 5, commands.BucketType.user)
    async def random_tag(self, ctx):
        """get a random tag"""
        tags = await db.get_tags(guild_id=ctx.guild.id)
        if not tags:
            return await ctx.reply(embed=self.error_embed(description="no tags found"))

        tag = random.choice(tags)
        await db.use_tag(tag["id"])
        await ctx.reply(f"**{tag['name']}**\n> {tag['content']}")

    @tag.command(name="search", aliases=["find"])
    @commands.cooldown(1, 5, commands.BucketType.user)
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
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def urban(self, ctx, *, query):
        """get a random urban dictionary definition"""
        try:
            async with self.bot.session.get(
                f"https://api.urbandictionary.com/v0/define?term={query}"
            ) as resp:
                if resp.status != 200:
                    await ctx.reply(
                        embed=self.error_embed(description="could not get definition")
                    )
                    return
                data = await resp.json()
        except Exception:
            return await ctx.reply(
                embed=self.error_embed(description="failed to fetch definition")
            )

        try:
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
        except Exception:
            return await ctx.reply(
                embed=self.error_embed(description="failed to process definition")
            )


async def setup(bot):
    await bot.add_cog(Fun(bot))
