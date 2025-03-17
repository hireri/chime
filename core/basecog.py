import discord
from discord.ext import commands
import logging
import datetime
import os
import sys
import platform
import psutil
from typing import Dict, List, Optional, Union, Any
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
        # You can implement global checks here, e.g., checking if the command is run in a guild
        # Return True to allow the command, False to deny it
        return True

    # Utility methods for creating embeds
    def embed(
        self, title: str = None, description: str = None, color: int = None
    ) -> discord.Embed:
        """create an embed with the main color"""
        # Check if config has been modified
        config.config.reload()

        return discord.Embed(
            title=title,
            description=description,
            color=color or config.MAIN_COLOR,
            timestamp=discord.utils.utcnow(),
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

    # Error handling
    async def cog_command_error(self, ctx, error):
        """handle errors for commands in this cog"""
        # Unwrap the error to get the original cause
        error = getattr(error, "original", error)

        # Handle specific error types
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(
                embed=self.error_embed(
                    title="permission denied",
                    description=f"you need {', '.join(error.missing_permissions)} permission(s) to use this command.",
                )
            )
            return

        if isinstance(error, commands.BotMissingPermissions):
            await ctx.send(
                embed=self.error_embed(
                    title="missing permissions",
                    description=f"i need {', '.join(error.missing_permissions)} permission(s) to execute this command.",
                )
            )
            return

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                embed=self.warning_embed(
                    title="cooldown",
                    description=f"this command is on cooldown. try again in {error.retry_after:.2f}s.",
                )
            )
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(
                embed=self.error_embed(
                    title="missing argument",
                    description=f"the {error.param.name} argument is required.",
                )
            )
            return

        if isinstance(error, commands.BadArgument):
            await ctx.send(
                embed=self.error_embed(title="invalid argument", description=str(error))
            )
            return

        # Log unhandled errors
        self.logger.error(f"Unhandled error in {ctx.command}: {error}", exc_info=error)
        await ctx.send(
            embed=self.error_embed(
                title="command error",
                description=f"an unexpected error occurred: {str(error)}",
            )
        )

    # Utility methods for UI components
    async def paginate(self, ctx, pages: List[discord.Embed], timeout: int = 60):
        """send paginated embeds with navigation buttons"""
        if not pages:
            return await ctx.send(
                embed=self.error_embed(description="no pages to display")
            )

        if len(pages) == 1:
            return await ctx.send(embed=pages[0])

        # Create view with enhanced navigation buttons
        class PaginationView(discord.ui.View):
            def __init__(self, pages):
                super().__init__(timeout=timeout)
                self.pages = pages
                self.current_page = 0

                # First page button
                self.add_item(
                    discord.ui.Button(
                        emoji=config.FIRST_ICON,
                        style=discord.ButtonStyle.gray,
                        custom_id="first",
                        row=0,
                    )
                )

                # Previous page button
                self.add_item(
                    discord.ui.Button(
                        emoji=config.PREV_ICON,
                        style=discord.ButtonStyle.gray,
                        custom_id="prev",
                        row=0,
                    )
                )

                # Page indicator/jump button
                self.add_item(
                    discord.ui.Button(
                        label=f"1/{len(pages)}",
                        emoji=config.PAGE_ICON,
                        style=discord.ButtonStyle.primary,
                        custom_id="page",
                        row=0,
                    )
                )

                # Next page button
                self.add_item(
                    discord.ui.Button(
                        emoji=config.NEXT_ICON,
                        style=discord.ButtonStyle.gray,
                        custom_id="next",
                        row=0,
                    )
                )

                # Last page button
                self.add_item(
                    discord.ui.Button(
                        emoji=config.LAST_ICON,
                        style=discord.ButtonStyle.gray,
                        custom_id="last",
                        row=0,
                    )
                )

                # Set callbacks for all buttons
                for child in self.children:
                    child.callback = self.button_callback

            async def button_callback(self, interaction: discord.Interaction):
                button_id = interaction.data["custom_id"]

                if interaction.user.id != ctx.author.id:
                    await interaction.response.send_message(
                        self.error_embed(
                            "You cannot use these controls as you didn't invoke the command."
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
                    # Create modal for page input
                    class PageInputModal(discord.ui.Modal, title="Jump to Page"):
                        page_number = discord.ui.TextInput(
                            label=f"Enter page number (1-{len(self.pages)})",
                            placeholder="Page number",
                            min_length=1,
                            max_length=len(str(len(self.pages))),
                        )

                        async def on_submit(
                            self, modal_interaction: discord.Interaction
                        ):
                            try:
                                page = int(self.page_number.value)
                                if 1 <= page <= len(self.pages):
                                    self.view.current_page = page - 1

                                    # Update the page button label
                                    for child in self.view.children:
                                        if child.custom_id == "page":
                                            child.label = (
                                                f"Page {page}/{len(self.view.pages)}"
                                            )

                                    await modal_interaction.response.edit_message(
                                        embed=self.view.pages[self.view.current_page],
                                        view=self.view,
                                    )
                                else:
                                    await modal_interaction.response.send_message(
                                        f"Please enter a number between 1 and {len(self.view.pages)}.",
                                        ephemeral=True,
                                    )
                            except ValueError:
                                await modal_interaction.response.send_message(
                                    "Please enter a valid number.", ephemeral=True
                                )

                    modal = PageInputModal()
                    modal.view = self
                    await interaction.response.send_modal(modal)
                    return

                # Update the page button label
                for child in self.children:
                    if child.custom_id == "page":
                        child.label = f"Page {self.current_page + 1}/{len(self.pages)}"

                await interaction.response.edit_message(
                    embed=self.pages[self.current_page], view=self
                )

            async def on_timeout(self):
                # Disable buttons when the view times out
                message = self.message
                if message:
                    try:
                        for child in self.children:
                            child.disabled = True
                        await message.edit(view=self)
                    except:
                        pass

        view = PaginationView(pages)
        view.message = await ctx.send(embed=pages[0], view=view)
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
        # Convert single embeds to lists for combined menu
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
            return await ctx.send(
                embed=self.error_embed(description="no categories to display")
            )

        # Create a view with both dropdown and pagination
        class CombinedView(discord.ui.View):
            def __init__(self, category_pages_dict):
                super().__init__(timeout=timeout)
                self.category_pages = category_pages_dict
                self.current_category = next(iter(category_pages_dict.keys()))
                self.current_page = 0

                # Create a dropdown with category options
                self.select = discord.ui.Select(
                    placeholder=placeholder,
                    options=[
                        discord.SelectOption(label=key, value=key)
                        for key in category_pages_dict.keys()
                    ],
                )

                # Set callback
                self.select.callback = self.dropdown_callback
                self.add_item(self.select)

                # Add pagination buttons if needed
                self.update_buttons()

            def update_buttons(self):
                # Remove any existing buttons
                for item in list(self.children):
                    if isinstance(item, discord.ui.Button):
                        self.remove_item(item)

                # Only add buttons if current category has multiple pages
                if len(self.category_pages[self.current_category]) > 1:
                    # First page button
                    self.add_item(
                        NavigationButton(
                            emoji=config.FIRST_ICON,
                            style=discord.ButtonStyle.gray,
                            custom_id="first",
                            row=1,
                        )
                    )

                    # Previous page button
                    self.add_item(
                        NavigationButton(
                            emoji=config.PREV_ICON,
                            style=discord.ButtonStyle.gray,
                            custom_id="prev",
                            row=1,
                        )
                    )

                    # Page indicator/jump button
                    total_pages = len(self.category_pages[self.current_category])
                    self.add_item(
                        PageButton(
                            label=f"{self.current_page + 1}/{total_pages}",
                            emoji=config.PAGE_ICON,
                            style=discord.ButtonStyle.primary,
                            custom_id="page",
                            row=1,
                        )
                    )

                    # Next page button
                    self.add_item(
                        NavigationButton(
                            emoji=config.NEXT_ICON,
                            style=discord.ButtonStyle.gray,
                            custom_id="next",
                            row=1,
                        )
                    )

                    # Last page button
                    self.add_item(
                        NavigationButton(
                            emoji=config.LAST_ICON,
                            style=discord.ButtonStyle.gray,
                            custom_id="last",
                            row=1,
                        )
                    )

            async def dropdown_callback(self, interaction: discord.Interaction):
                self.current_category = self.select.values[0]
                self.current_page = 0  # Reset to first page when changing categories

                # Update buttons based on the new category
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
                    except:
                        pass

        # Custom button class for navigation
        class NavigationButton(discord.ui.Button):
            async def callback(self, interaction: discord.Interaction):
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

                # Update the page button label
                for child in view.children:
                    if isinstance(child, PageButton):
                        child.label = f"Page {view.current_page + 1}/{len(pages)}"

                await interaction.response.edit_message(
                    embed=pages[view.current_page], view=view
                )

        # Page jump button with modal
        class PageButton(discord.ui.Button):
            async def callback(self, interaction: discord.Interaction):
                view = self.view
                pages = view.category_pages[view.current_category]

                # Create modal for page input
                class PageInputModal(discord.ui.Modal, title="Jump to Page"):
                    page_number = discord.ui.TextInput(
                        label=f"Enter page number (1-{len(pages)})",
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
                                    f"Please enter a number between 1 and {len(pages)}.",
                                    ephemeral=True,
                                )
                        except ValueError:
                            await modal_interaction.response.send_message(
                                "Please enter a valid number.", ephemeral=True
                            )

                await interaction.response.send_modal(PageInputModal())

        # Get the first category and page
        first_category = next(iter(category_pages.keys()))
        first_page = category_pages[first_category][0]

        # Create and send view
        view = CombinedView(category_pages)
        view.message = await ctx.send(embed=first_page, view=view)
        return view.message
