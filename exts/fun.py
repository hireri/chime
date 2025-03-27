import discord
import asyncio
import config
from urllib.parse import urlparse
from discord.ext import commands
from core.basecog import BaseCog
import googlesearch
import duckduckgo_images_api
from itertools import islice


class Fun(BaseCog):
    def gen(self, generator, group_size=3):
        while True:
            group = list(islice(generator, group_size))

            if not group:
                break

            yield group

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

        await ctx.send(embed=self.error_embed(description="no results found"))

    @commands.command(name="image", brief="search for an image")
    async def image(self, ctx, *, query):
        await ctx.message.add_reaction(config.THINK_ICON)
        try:
            results = await self.image_search(query)
            await self.paginate(ctx, results)
        except:
            await ctx.send(embed=self.error_embed(description="no results found"))
        await ctx.message.remove_reaction(config.THINK_ICON, self.bot.user)


async def setup(bot):
    await bot.add_cog(Fun(bot))
