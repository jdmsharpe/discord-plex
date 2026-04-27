from collections.abc import Callable
from typing import Any

from discord import ButtonStyle, Interaction, SelectOption
from discord.ui import Button, Select, View, button

from .models import CachedMedia, OverseerrSearchResult


class MediaSelectView(View):
    """View with a select menu for choosing media."""

    def __init__(
        self,
        media_items: list[CachedMedia],
        callback: Callable[[Interaction, CachedMedia], Any],
        placeholder: str = "Select media...",
        timeout: float | None = None,  # No timeout - let users take their time
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
        timeout: float | None = None,  # No timeout - let users take their time
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
    """Simple confirm/cancel view."""

    def __init__(
        self,
        confirm_callback: Callable[[Interaction], Any],
        cancel_callback: Callable[[Interaction], Any] | None = None,
        confirm_label: str = "Confirm",
        cancel_label: str = "Cancel",
        timeout: float | None = None,
    ):
        super().__init__(timeout=timeout)
        self.confirm_callback = confirm_callback
        self.cancel_callback = cancel_callback
        self._confirm_label = confirm_label
        self._cancel_label = cancel_label
        self._update_labels()

    def _update_labels(self) -> None:
        """Update button labels after initialization."""
        for child in self.children:
            if isinstance(child, Button):
                if child.custom_id == "confirm":
                    child.label = self._confirm_label
                elif child.custom_id == "cancel":
                    child.label = self._cancel_label

    @button(label="Confirm", style=ButtonStyle.success, custom_id="confirm")
    async def confirm_btn(self, button: Button, interaction: Interaction) -> None:
        await interaction.response.defer()
        await self.confirm_callback(interaction)

    @button(label="Cancel", style=ButtonStyle.secondary, custom_id="cancel")
    async def cancel_btn(self, button: Button, interaction: Interaction) -> None:
        await interaction.response.defer()
        if self.cancel_callback:
            await self.cancel_callback(interaction)


class MediaInfoView(View):
    """View for media info with Open in Plex button."""

    def __init__(
        self,
        media: CachedMedia,
        plex_web_url: str | None = None,
        timeout: float | None = None,
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
        cancel_callback: Callable[[Interaction], Any] | None = None,
        timeout: float | None = None,
    ):
        super().__init__(timeout=timeout)
        self.seasons = [s for s in seasons if s.get("seasonNumber", 0) > 0]  # Exclude specials
        self.confirm_callback = confirm_callback
        self.cancel_callback = cancel_callback
        self.selected_seasons: list[int] = []

        # Build season options
        options = []
        for season in self.seasons:
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
                max_values=len(options),  # Allow selecting all
            )
            self.select.callback = self._handle_select
            self.add_item(self.select)

    async def _handle_select(self, interaction: Interaction) -> None:
        """Handle season selection - store selected seasons."""
        self.selected_seasons = [int(v) for v in self.select.values]
        # Update the select menu to show selection
        await interaction.response.defer()

    @button(label="Request Selected", style=ButtonStyle.success, custom_id="confirm", row=1)
    async def confirm_btn(self, button: Button, interaction: Interaction) -> None:
        if not self.selected_seasons:
            await interaction.response.send_message(
                "Please select at least one season first!", ephemeral=True
            )
            return
        await interaction.response.defer()
        await self.confirm_callback(interaction, self.selected_seasons)

    @button(label="Cancel", style=ButtonStyle.secondary, custom_id="cancel", row=1)
    async def cancel_btn(self, button: Button, interaction: Interaction) -> None:
        await interaction.response.defer()
        if self.cancel_callback:
            await self.cancel_callback(interaction)
