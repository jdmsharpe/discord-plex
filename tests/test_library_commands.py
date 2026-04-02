from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from discord_plex.cogs.plex.library import plex_search, show_media_info
from discord_plex.cogs.plex.models import CachedMedia, MediaType
from discord_plex.cogs.plex.views import MediaInfoView, MediaSelectView


@pytest.fixture
def media_item() -> CachedMedia:
    return CachedMedia(
        rating_key="1",
        title="Example Movie",
        year=2024,
        media_type=MediaType.MOVIE,
        library="Movies",
        thumb="/library/metadata/1/thumb/123",
        tmdb_id=123,
    )


@pytest.mark.asyncio
async def test_show_media_info_sends_single_followup_with_media_view(media_item: CachedMedia):
    ctx = SimpleNamespace(send_followup=AsyncMock())
    cog = SimpleNamespace(
        overseerr_client=SimpleNamespace(get_poster_url=AsyncMock(return_value="https://img/poster.jpg")),
        plex_client=SimpleNamespace(
            get_thumb_url=Mock(return_value="https://plex/thumb.jpg"),
            server=SimpleNamespace(machineIdentifier="server-1"),
        ),
        logger=Mock(),
    )

    await show_media_info(cog, ctx, media_item)

    ctx.send_followup.assert_awaited_once()
    kwargs = ctx.send_followup.await_args.kwargs
    assert kwargs["embed"].title == "🎬 Example Movie (2024)"
    assert isinstance(kwargs["view"], MediaInfoView)


@pytest.mark.asyncio
async def test_plex_search_select_flow_uses_same_response_path(
    media_item: CachedMedia,
    monkeypatch: pytest.MonkeyPatch,
):
    second_item = CachedMedia(
        rating_key="2",
        title="Another Movie",
        year=2020,
        media_type=MediaType.MOVIE,
        library="Movies",
    )
    results = [media_item, second_item]

    ctx = SimpleNamespace(defer=AsyncMock(), send_followup=AsyncMock())
    cog = SimpleNamespace(
        cache=SimpleNamespace(
            is_stale=False,
            search=Mock(return_value=results),
        ),
        plex_client=SimpleNamespace(search=Mock(return_value=[])),
    )

    show_media_info_mock = AsyncMock()
    monkeypatch.setattr("discord_plex.cogs.plex.library.show_media_info", show_media_info_mock)

    await plex_search(cog, ctx, "movie")

    ctx.send_followup.assert_awaited_once()
    initial_view = ctx.send_followup.await_args.kwargs["view"]
    assert isinstance(initial_view, MediaSelectView)

    interaction = SimpleNamespace(response=SimpleNamespace(defer=AsyncMock()))
    initial_view.select._selected_values = [second_item.rating_key]
    initial_view.select._interaction = SimpleNamespace(data={})
    await initial_view.select.callback(interaction)

    interaction.response.defer.assert_awaited_once()
    show_media_info_mock.assert_awaited_once_with(cog, ctx, second_item)
