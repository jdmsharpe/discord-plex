from typing import Callable, Optional, Any
import discord
from discord import ButtonStyle, Interaction, SelectOption
from discord.ui import Button, Select, View, button

from .models import CachedMedia, OverseerrSearchResult


class PaginationView(View):
    """Generic pagination view for lists."""

    def __init__(
        self,
        items: list[Any],
        per_page: int,
        embed_generator: Callable[[list[Any], int, int], discord.Embed],
        timeout: Optional[float] = None,
    ):
        super().__init__(timeout=timeout)
        self.items = items
        self.per_page = per_page
        self.embed_generator = embed_generator
        self.current_page = 1
        self.total_pages = max(1, (len(items) + per_page - 1) // per_page)
        self._update_buttons()

    def _update_buttons(self) -> None:
        """Update button states based on current page."""
        for child in self.children:
            if isinstance(child, Button):
                if child.custom_id == "prev":
                    child.disabled = self.current_page <= 1
                elif child.custom_id == "next":
                    child.disabled = self.current_page >= self.total_pages

    def get_current_embed(self) -> discord.Embed:
        """Get embed for current page."""
        start = (self.current_page - 1) * self.per_page
        end = min(start + self.per_page, len(self.items))
        page_items = self.items[start:end]
        return self.embed_generator(page_items, self.current_page, self.total_pages)

    @button(label="◀️ Prev", style=ButtonStyle.secondary, custom_id="prev")
    async def prev_button(self, button: Button, interaction: Interaction) -> None:
        if self.current_page > 1:
            self.current_page -= 1
            self._update_buttons()
            await interaction.response.edit_message(
                embed=self.get_current_embed(),
                view=self,
            )
        else:
            await interaction.response.defer()

    @button(label="Next ▶️", style=ButtonStyle.secondary, custom_id="next")
    async def next_button(self, button: Button, interaction: Interaction) -> None:
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._update_buttons()
            await interaction.response.edit_message(
                embed=self.get_current_embed(),
                view=self,
            )
        else:
            await interaction.response.defer()


class MediaSelectView(View):
    """View with a select menu for choosing media."""

    def __init__(
        self,
        media_items: list[CachedMedia],
        callback: Callable[[Interaction, CachedMedia], Any],
        placeholder: str = "Select media...",
        timeout: Optional[float] = None,  # No timeout - let users take their time
    ):
        super().__init__(timeout=timeout)
        self.media_items = media_items[:25]  # Discord limit
        self.callback = callback

        # Build options
        options = []
        for item in self.media_items:
            year_str = f" ({item.year})" if item.year else ""
            label = f"{item.title}{year_str}"[:100]  # Max label length
            description = item.library[:100] if item.library else None
            options.append(
                SelectOption(
                    label=label,
                    value=item.rating_key,
                    emoji=item.type_emoji,
                    description=description,
                )
            )

        self.select = Select(
            placeholder=placeholder,
            options=options,
            min_values=1,
            max_values=1,
        )
        self.select.callback = self._handle_select
        self.add_item(self.select)

    async def _handle_select(self, interaction: Interaction) -> None:
        """Handle selection."""
        selected_key = self.select.values[0]
        selected_item = next(
            (m for m in self.media_items if m.rating_key == selected_key),
            None,
        )
        if selected_item:
            await self.callback(interaction, selected_item)


class RequestSelectView(View):
    """View with a select menu for choosing search results to request."""

    def __init__(
        self,
        results: list[OverseerrSearchResult],
        callback: Callable[[Interaction, OverseerrSearchResult], Any],
        placeholder: str = "Select to request...",
        timeout: Optional[float] = None,  # No timeout - let users take their time
    ):
        super().__init__(timeout=timeout)
        self.results = results[:25]
        self.callback = callback

        options = []
        for result in self.results:
            year_str = f" ({result.year})" if result.year else ""
            label = f"{result.title}{year_str}"[:100]

            # Status description
            if result.already_available:
                description = "Already available"
            elif result.already_requested:
                description = "Already requested"
            else:
                description = "Available to request"

            options.append(
                SelectOption(
                    label=label,
                    value=str(result.tmdb_id),
                    emoji=result.type_emoji,
                    description=description,
                )
            )

        self.select = Select(
            placeholder=placeholder,
            options=options,
            min_values=1,
            max_values=1,
        )
        self.select.callback = self._handle_select
        self.add_item(self.select)

    async def _handle_select(self, interaction: Interaction) -> None:
        """Handle selection."""
        selected_value: str = self.select.values[0]  # type: ignore[assignment]
        selected_id = int(selected_value)
        selected_result = next(
            (r for r in self.results if r.tmdb_id == selected_id),
            None,
        )
        if selected_result:
            await self.callback(interaction, selected_result)


class ConfirmView(View):
    """Simple confirm view."""

    def __init__(
        self,
        confirm_callback: Callable[[Interaction], Any],
        confirm_label: str = "Confirm",
        timeout: Optional[float] = None,
    ):
        super().__init__(timeout=timeout)
        self.confirm_callback = confirm_callback
        self._confirm_label = confirm_label
        self._update_labels()

    def _update_labels(self) -> None:
        """Update button labels after initialization."""
        for child in self.children:
            if isinstance(child, Button):
                if child.custom_id == "confirm":
                    child.label = self._confirm_label

    @button(label="Confirm", style=ButtonStyle.success, custom_id="confirm")
    async def confirm_btn(self, button: Button, interaction: Interaction) -> None:
        await interaction.response.defer()
        await self.confirm_callback(interaction)


class RequestActionView(View):
    """View for admin actions on requests (approve/deny)."""

    def __init__(
        self,
        request_id: int,
        approve_callback: Callable[[Interaction, int], Any],
        deny_callback: Callable[[Interaction, int], Any],
        timeout: Optional[float] = None,
    ):
        super().__init__(timeout=timeout)
        self.request_id = request_id
        self.approve_callback = approve_callback
        self.deny_callback = deny_callback

    @button(label="Approve", style=ButtonStyle.success, emoji="✅", custom_id="approve")
    async def approve_btn(self, button: Button, interaction: Interaction) -> None:
        await interaction.response.defer()
        await self.approve_callback(interaction, self.request_id)

    @button(label="Deny", style=ButtonStyle.danger, emoji="❌", custom_id="deny")
    async def deny_btn(self, button: Button, interaction: Interaction) -> None:
        await interaction.response.defer()
        await self.deny_callback(interaction, self.request_id)


class MediaInfoView(View):
    """View for media info with Open in Plex button."""

    def __init__(
        self,
        media: CachedMedia,
        plex_web_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        super().__init__(timeout=timeout)

        if plex_web_url:
            self.add_item(
                Button(
                    label="Open in Plex",
                    style=ButtonStyle.link,
                    url=plex_web_url,
                    emoji="▶️",
                )
            )


class SeasonSelectView(View):
    """View for selecting which seasons to request for a TV show."""

    def __init__(
        self,
        seasons: list[dict],  # List of {"seasonNumber": int, "episodeCount": int}
        confirm_callback: Callable[[Interaction, list[int]], Any],
        timeout: Optional[float] = None,
    ):
        super().__init__(timeout=timeout)
        self.seasons = [s for s in seasons if s.get("seasonNumber", 0) > 0]  # Exclude specials
        self.confirm_callback = confirm_callback
        self.selected_seasons: list[int] = []
        self.requested_seasons: list[int] = []  # Track already-requested seasons

        self._build_select()

    def _build_select(self) -> None:
        """Build or rebuild the season select menu."""
        # Remove existing select if present
        for child in list(self.children):
            if isinstance(child, Select):
                self.remove_item(child)

        # Build season options, excluding already-requested seasons
        available_seasons = [
            s for s in self.seasons
            if s.get("seasonNumber", 0) not in self.requested_seasons
        ]

        if not available_seasons:
            return

        options = []
        for season in available_seasons:
            season_num = season.get("seasonNumber", 0)
            episode_count = season.get("episodeCount", 0)
            options.append(
                SelectOption(
                    label=f"Season {season_num}",
                    value=str(season_num),
                    description=f"{episode_count} episodes",
                )
            )

        if options:
            self.select = Select(
                placeholder="Select seasons to request...",
                options=options,
                min_values=1,
                max_values=len(options),  # Allow selecting all available
            )
            self.select.callback = self._handle_select
            # Insert at the beginning so it appears before the button
            self.add_item(self.select)

    async def _handle_select(self, interaction: Interaction) -> None:
        """Handle season selection - store selected seasons."""
        self.selected_seasons = [int(v) for v in self.select.values]
        await interaction.response.defer()

    @button(label="Request Selected", style=ButtonStyle.success, custom_id="confirm", row=1)
    async def confirm_btn(self, button: Button, interaction: Interaction) -> None:
        if not self.selected_seasons:
            await interaction.response.send_message(
                "Please select at least one season first!", ephemeral=True
            )
            return
        await interaction.response.defer()

        # Store the seasons being requested before callback
        seasons_to_request = self.selected_seasons.copy()

        # Call the callback with selected seasons
        await self.confirm_callback(interaction, seasons_to_request)

        # Mark these seasons as requested
        self.requested_seasons.extend(seasons_to_request)
        self.selected_seasons = []

        # Rebuild the select menu without the requested seasons
        self._build_select()

        # Update the view - if there are still seasons available, show updated view
        if any(s.get("seasonNumber", 0) not in self.requested_seasons for s in self.seasons):
            await interaction.message.edit(view=self)
        else:
            # All seasons have been requested, disable the button
            self.confirm_btn.disabled = True
            self.confirm_btn.label = "All Seasons Requested"
            await interaction.message.edit(view=self)
