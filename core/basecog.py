import logging
from typing import Dict, List

import discord
from discord.ext import commands

import config


class BaseCog(commands.Cog):
    """base cog class that all other cogs should inherit from"""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(f"cog.{self.__class__.__name__}")

    async def cog_load(self):
        """called when the cog is loaded"""
        self.logger.info(f"cog {self.__class__.__name__} loaded")

    async def cog_unload(self):
        """called when the cog is unloaded"""
        self.logger.info(f"cog {self.__class__.__name__} unloaded")

    async def cog_check(self, ctx):
        """global check for all commands in this cog"""
        return True

    def embed(
        self,
        title: str = None,
        description: str = None,
        color: int = None,
        show_time=False,
    ) -> discord.Embed:
        """create an embed with the main color"""
        config.config.reload()

        return discord.Embed(
            title=title,
            description=description,
            color=color or config.MAIN_COLOR,
            timestamp=discord.utils.utcnow() if show_time else None,
        )

    def success_embed(
        self, title: str = None, description: str = None
    ) -> discord.Embed:
        """create a success embed"""
        return self.embed(
            title=title,
            description=f"{config.SUCCESS_ICON} {description}" if description else None,
            color=config.SUCCESS_COLOR,
        )

    def error_embed(self, title: str = None, description: str = None) -> discord.Embed:
        """create an error embed"""
        return self.embed(
            title=title,
            description=f"{config.ERROR_ICON} {description}" if description else None,
            color=config.ERROR_COLOR,
        )

    def warning_embed(
        self, title: str = None, description: str = None
    ) -> discord.Embed:
        """create a warning embed"""
        return self.embed(
            title=title,
            description=f"{config.WARN_ICON} {description}" if description else None,
            color=config.WARN_COLOR,
        )

    async def paginate(
        self,
        ctx,
        pages: List[discord.Embed],
        timeout: int = 60,
        compact=False,
        extra_buttons=None,
    ):
        """send paginated embeds with navigation buttons"""
        if not pages:
            return await ctx.reply(
                embed=self.error_embed(description="no pages to display")
            )

        class PaginationView(discord.ui.View):
            def __init__(self, pages, outer):
                super().__init__(timeout=timeout)
                self.pages = pages
                self.current_page = 0
                self.outer = outer

                if len(pages) > 1:
                    if not compact:
                        self.add_item(
                            discord.ui.Button(
                                emoji=config.FIRST_ICON,
                                style=discord.ButtonStyle.gray,
                                custom_id="first",
                                row=0,
                            )
                        )

                    self.add_item(
                        discord.ui.Button(
                            emoji=config.PREV_ICON,
                            style=discord.ButtonStyle.gray,
                            custom_id="prev",
                            row=0,
                        )
                    )

                    self.add_item(
                        discord.ui.Button(
                            label=f"1/{len(pages)}",
                            emoji=config.PAGE_ICON,
                            style=discord.ButtonStyle.primary,
                            custom_id="page",
                            row=0,
                        )
                    )

                    self.add_item(
                        discord.ui.Button(
                            emoji=config.NEXT_ICON,
                            style=discord.ButtonStyle.gray,
                            custom_id="next",
                            row=0,
                        )
                    )

                    if not compact:
                        self.add_item(
                            discord.ui.Button(
                                emoji=config.LAST_ICON,
                                style=discord.ButtonStyle.gray,
                                custom_id="last",
                                row=0,
                            )
                        )

                if extra_buttons:
                    for button in extra_buttons:
                        self.add_item(button)

                for child in self.children:
                    if child in extra_buttons:
                        continue
                    child.callback = self.button_callback

            async def button_callback(self, interaction: discord.Interaction):
                button_id = interaction.data["custom_id"]

                if interaction.user.id != ctx.author.id:
                    await interaction.response.send_message(
                        embed=self.outer.error_embed(
                            description="you cannot use these controls"
                        ),
                        ephemeral=True,
                    )
                    return

                if button_id == "first":
                    self.current_page = 0
                elif button_id == "prev":
                    self.current_page = (self.current_page - 1) % len(self.pages)
                elif button_id == "next":
                    self.current_page = (self.current_page + 1) % len(self.pages)
                elif button_id == "last":
                    self.current_page = len(self.pages) - 1
                elif button_id == "page":

                    class PageInputModal(discord.ui.Modal, title="Jump to Page"):
                        page_number = discord.ui.TextInput(
                            label=f"enter page number (1-{len(self.pages)})",
                            placeholder="page number",
                            min_length=1,
                            max_length=len(str(len(self.pages))),
                        )

                        async def on_submit(
                            self, modal_interaction: discord.Interaction
                        ):
                            try:
                                page = int(self.page_number.value)
                                if 1 <= page <= len(self.view.pages):
                                    self.view.current_page = page - 1

                                    for child in self.view.children:
                                        if child.custom_id == "page":
                                            child.label = (
                                                f"{page}/{len(self.view.pages)}"
                                            )

                                    await modal_interaction.response.edit_message(
                                        embed=self.view.pages[self.view.current_page],
                                        view=self.view,
                                    )
                                else:
                                    await modal_interaction.response.send_message(
                                        f"enter a number between 1 and {len(self.view.pages)}",
                                        ephemeral=True,
                                    )
                            except ValueError:
                                await modal_interaction.response.send_message(
                                    "enter a valid number", ephemeral=True
                                )

                    modal = PageInputModal()
                    modal.view = self
                    await interaction.response.send_modal(modal)
                    return

                for child in self.children:
                    if child.custom_id == "page":
                        child.label = f"{self.current_page + 1}/{len(self.pages)}"

                await interaction.response.edit_message(
                    embed=self.pages[self.current_page], view=self
                )

            async def on_timeout(self):
                message = self.message
                if message:
                    try:
                        for child in self.children:
                            child.disabled = True
                        await message.edit(view=self)
                    except Exception:
                        pass

        view = PaginationView(pages, self)
        view.message = await ctx.reply(embed=pages[0], view=view)
        return view.message

    async def create_dropdown_menu(
        self,
        ctx,
        embeds: Dict[str, discord.Embed],
        placeholder: str = "select an option...",
        timeout: int = 60,
    ):
        """send a message with dropdown navigation for multiple embeds

        Args:
            ctx: The command context
            embeds: A dictionary mapping option names to embeds
            placeholder: The dropdown placeholder text
            timeout: Timeout in seconds

        Returns:
            The sent message
        """
        category_pages = {key: [embed] for key, embed in embeds.items()}
        return await self.create_combined_menu(
            ctx, category_pages, placeholder, timeout
        )

    async def create_combined_menu(
        self,
        ctx,
        category_pages: Dict[str, List[discord.Embed]],
        placeholder: str = "select a category...",
        timeout: int = 60,
    ):
        """send a message with both dropdown categories and pagination for pages within each category

        Args:
            ctx: The command context
            category_pages: A dictionary mapping category names to lists of embed pages
            placeholder: The dropdown placeholder text
            timeout: Timeout in seconds

        Returns:
            The sent message
        """
        if not category_pages:
            return await ctx.reply(
                embed=self.error_embed(description="no categories to display")
            )

        class CombinedView(discord.ui.View):
            def __init__(self, category_pages_dict, outer):
                super().__init__(timeout=timeout)
                self.category_pages = category_pages_dict
                self.current_category = next(iter(category_pages_dict.keys()))
                self.current_page = 0
                self.outer = outer

                self.select = discord.ui.Select(
                    placeholder=placeholder,
                    options=[
                        discord.SelectOption(label=key, value=key)
                        for key in category_pages_dict.keys()
                    ],
                )

                self.select.callback = self.dropdown_callback
                self.add_item(self.select)

                self.update_buttons()

            def update_buttons(self):
                for item in list(self.children):
                    if isinstance(item, discord.ui.Button):
                        self.remove_item(item)

                if len(self.category_pages[self.current_category]) > 1:
                    self.add_item(
                        NavigationButton(
                            emoji=config.FIRST_ICON,
                            style=discord.ButtonStyle.gray,
                            custom_id="first",
                            row=1,
                            outer=self.outer,
                        )
                    )

                    self.add_item(
                        NavigationButton(
                            emoji=config.PREV_ICON,
                            style=discord.ButtonStyle.gray,
                            custom_id="prev",
                            row=1,
                            outer=self.outer,
                        )
                    )

                    total_pages = len(self.category_pages[self.current_category])
                    self.add_item(
                        PageButton(
                            label=f"{self.current_page + 1}/{total_pages}",
                            emoji=config.PAGE_ICON,
                            style=discord.ButtonStyle.primary,
                            custom_id="page",
                            row=1,
                            outer=self.outer,
                        )
                    )

                    self.add_item(
                        NavigationButton(
                            emoji=config.NEXT_ICON,
                            style=discord.ButtonStyle.gray,
                            custom_id="next",
                            row=1,
                            outer=self.outer,
                        )
                    )

                    self.add_item(
                        NavigationButton(
                            emoji=config.LAST_ICON,
                            style=discord.ButtonStyle.gray,
                            custom_id="last",
                            row=1,
                            outer=self.outer,
                        )
                    )

            async def dropdown_callback(self, interaction: discord.Interaction):
                if interaction.user.id != ctx.author.id:
                    await interaction.response.send_message(
                        embed=self.outer.error_embed(
                            description="you cannot use these controls"
                        ),
                        ephemeral=True,
                    )
                    return
                self.current_category = self.select.values[0]
                self.current_page = 0

                self.update_buttons()

                await interaction.response.edit_message(
                    embed=self.category_pages[self.current_category][self.current_page],
                    view=self,
                )

            async def on_timeout(self):
                message = self.message
                if message:
                    try:
                        for child in self.children:
                            child.disabled = True
                        await message.edit(view=self)
                    except Exception:
                        pass

        class NavigationButton(discord.ui.Button):
            def __init__(self, outer, **kwargs):
                super().__init__(**kwargs)
                self.outer = outer

            async def callback(self, interaction: discord.Interaction):
                if interaction.user.id != ctx.author.id:
                    await interaction.response.send_message(
                        embed=self.outer.error_embed(
                            description="you cannot use these controls"
                        ),
                        ephemeral=True,
                    )
                    return

                view = self.view
                pages = view.category_pages[view.current_category]

                if self.custom_id == "first":
                    view.current_page = 0
                elif self.custom_id == "prev":
                    view.current_page = (view.current_page - 1) % len(pages)
                elif self.custom_id == "next":
                    view.current_page = (view.current_page + 1) % len(pages)
                elif self.custom_id == "last":
                    view.current_page = len(pages) - 1

                for child in view.children:
                    if isinstance(child, PageButton):
                        child.label = f"{view.current_page + 1}/{len(pages)}"

                await interaction.response.edit_message(
                    embed=pages[view.current_page], view=view
                )

        class PageButton(discord.ui.Button):
            def __init__(self, outer, **kwargs):
                super().__init__(**kwargs)
                self.outer = outer

            async def callback(self, interaction: discord.Interaction):
                if interaction.user.id != ctx.author.id:
                    await interaction.response.send_message(
                        embed=self.outer.error_embed(
                            description="you cannot use these controls"
                        ),
                        ephemeral=True,
                    )
                    return
                view = self.view
                pages = view.category_pages[view.current_category]

                class PageInputModal(discord.ui.Modal, title="jump to page"):
                    page_number = discord.ui.TextInput(
                        label=f"enter page number (1-{len(pages)})",
                        placeholder="Page number",
                        min_length=1,
                        max_length=len(str(len(pages))),
                    )

                    async def on_submit(self, modal_interaction: discord.Interaction):
                        try:
                            page = int(self.page_number.value)
                            if 1 <= page <= len(pages):
                                view.current_page = page - 1
                                await modal_interaction.response.edit_message(
                                    embed=pages[view.current_page], view=view
                                )
                            else:
                                await modal_interaction.response.send_message(
                                    f"enter a number between 1 and {len(pages)}.",
                                    ephemeral=True,
                                )
                        except ValueError:
                            await modal_interaction.response.send_message(
                                "enter a valid number.", ephemeral=True
                            )

                await interaction.response.send_modal(PageInputModal())

        first_category = next(iter(category_pages.keys()))
        first_page = category_pages[first_category][0]

        view = CombinedView(category_pages, self)
        view.message = await ctx.reply(embed=first_page, view=view)
        return view.message
