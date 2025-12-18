import logging
from typing import Optional

from plexapi.server import PlexServer
from plexapi.exceptions import NotFound

from .models import (
    CachedMedia,
    MediaType,
    ActiveStream,
    PlexClient,
)


logger = logging.getLogger(__name__)


class PlexClientWrapper:
    """Wrapper for Plex Media Server API interactions."""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._server: Optional[PlexServer] = None

    @property
    def server(self) -> PlexServer:
        """Lazy-load the Plex server connection."""
        if self._server is None:
            self._server = PlexServer(self.base_url, self.token)
        return self._server

    def reconnect(self) -> None:
        """Force reconnection to server."""
        self._server = None

    def get_thumb_url(self, thumb_path: Optional[str]) -> Optional[str]:
        """Convert Plex thumb path to full URL with token."""
        if not thumb_path:
            return None
        return f"{self.base_url}{thumb_path}?X-Plex-Token={self.token}"

    def get_all_media(self) -> list[CachedMedia]:
        """Fetch all media from all libraries for caching."""
        media_items = []

        try:
            for section in self.server.library.sections():
                section_type = section.type
                logger.info(f"Scanning library: {section.title} ({section_type})")

                if section_type in ("movie", "show", "artist"):
                    for item in section.all():
                        cached = self._convert_to_cached_media(item, section.title)
                        if cached:
                            media_items.append(cached)

        except Exception as e:
            logger.error(f"Error fetching media library: {e}")
            raise

        logger.info(f"Cached {len(media_items)} media items")
        return media_items

    def _convert_to_cached_media(
        self, item, library_name: str
    ) -> Optional[CachedMedia]:
        """Convert a Plex media item to CachedMedia."""
        try:
            media_type = self._get_media_type(item.type)
            if not media_type:
                return None

            cached = CachedMedia(
                rating_key=str(item.ratingKey),
                title=item.title,
                year=getattr(item, "year", None),
                media_type=media_type,
                library=library_name,
                thumb=item.thumb if hasattr(item, "thumb") else None,
                summary=getattr(item, "summary", None),
                rating=getattr(item, "rating", None),
                duration=getattr(item, "duration", None),
                added_at=getattr(item, "addedAt", None),
            )

            # Add show-specific info
            if media_type == MediaType.SHOW:
                cached.episode_count = getattr(item, "leafCount", None)
                cached.season_count = getattr(item, "childCount", None)

            return cached

        except Exception as e:
            logger.warning(
                f"Error converting media item {getattr(item, 'title', 'unknown')}: {e}"
            )
            return None

    @staticmethod
    def _get_media_type(plex_type: str) -> Optional[MediaType]:
        """Convert Plex type string to MediaType enum."""
        type_map = {
            "movie": MediaType.MOVIE,
            "show": MediaType.SHOW,
            "episode": MediaType.EPISODE,
            "season": MediaType.SEASON,
            "artist": MediaType.ARTIST,
            "album": MediaType.ALBUM,
            "track": MediaType.TRACK,
        }
        return type_map.get(plex_type)

    def search(self, query: str, limit: int = 10) -> list[CachedMedia]:
        """Search Plex library directly."""
        results = []
        try:
            search_results = self.server.search(query, limit=limit)
            for item in search_results:
                if item.type in ("movie", "show", "artist", "album"):
                    library_name = self._get_library_for_item(item)
                    cached = self._convert_to_cached_media(item, library_name)
                    if cached:
                        results.append(cached)
        except Exception as e:
            logger.error(f"Error searching Plex: {e}")
        return results

    def _get_library_for_item(self, item) -> str:
        """Get library name for a media item."""
        try:
            return item.librarySectionTitle
        except AttributeError:
            return "Unknown"

    def get_item_by_key(self, rating_key: str) -> Optional[CachedMedia]:
        """Get a specific item by rating key."""
        try:
            item = self.server.fetchItem(int(rating_key))
            library_name = self._get_library_for_item(item)
            return self._convert_to_cached_media(item, library_name)
        except NotFound:
            logger.warning(f"Item not found: {rating_key}")
            return None
        except Exception as e:
            logger.error(f"Error fetching item {rating_key}: {e}")
            return None

    def get_active_streams(self) -> list[ActiveStream]:
        """Get all currently active streams."""
        streams = []
        try:
            sessions = self.server.sessions()
            logger.debug(f"Fetching active streams: found {len(sessions)} sessions")
            for session in sessions:
                stream = self._convert_to_active_stream(session)
                if stream:
                    streams.append(stream)
            logger.info(f"Active streams: {len(streams)} currently playing")
        except Exception as e:
            logger.error(f"Error fetching active streams: {e}")
        return streams

    def _convert_to_active_stream(self, session) -> Optional[ActiveStream]:
        """Convert a Plex session to ActiveStream."""
        try:
            # Get player info
            player = session.players[0] if session.players else None
            player_name = player.title if player else None
            player_device = player.device if player else None

            # Get transcode info
            transcode_session = (
                session.transcodeSessions[0] if session.transcodeSessions else None
            )
            transcode_decision = None
            quality = None

            if transcode_session:
                transcode_decision = "Transcode"
                quality = f"{transcode_session.videoDecision}"
            else:
                transcode_decision = "Direct Play"

            # Get quality from media
            if session.media and session.media[0]:
                media = session.media[0]
                if hasattr(media, "videoResolution"):
                    resolution = str(media.videoResolution)
                    # Avoid "1080pp" - only add "p" if not already present
                    quality = resolution if resolution.endswith("p") else f"{resolution}p"

            # Calculate progress
            view_offset = getattr(session, "viewOffset", 0) or 0
            duration = getattr(session, "duration", 1) or 1
            progress_percent = (view_offset / duration) * 100 if duration > 0 else 0

            # Determine state
            state = "playing"
            if player and hasattr(player, "state"):
                state = player.state

            # Build full title - include show name for episodes
            media_title = session.title
            if session.type == "episode":
                show_title = getattr(session, "grandparentTitle", None)
                season_num = getattr(session, "parentIndex", None)
                episode_num = getattr(session, "index", None)
                if show_title:
                    if season_num and episode_num:
                        media_title = f"{show_title} - S{season_num:02d}E{episode_num:02d} - {session.title}"
                    else:
                        media_title = f"{show_title} - {session.title}"

            return ActiveStream(
                session_key=str(session.sessionKey),
                media_title=media_title,
                media_year=getattr(session, "grandparentYear", None) or getattr(session, "year", None),
                media_type=self._get_media_type(session.type) or MediaType.MOVIE,
                thumb=session.thumb if hasattr(session, "thumb") else None,
                progress_percent=progress_percent,
                progress_time=view_offset,
                duration=duration,
                state=state,
                quality=quality,
                transcode_decision=transcode_decision,
                player_name=player_name,
                player_device=player_device,
            )
        except Exception as e:
            logger.warning(f"Error converting session: {e}")
            return None

    def get_recently_added(
        self, library: Optional[str] = None, limit: int = 10
    ) -> list[CachedMedia]:
        """Get recently added media."""
        logger.debug(f"Fetching recently added: library={library or 'all'}, limit={limit}")
        results = []
        try:
            if library:
                # Search specific library - section.recentlyAdded accepts maxresults
                for section in self.server.library.sections():
                    if section.title.lower() == library.lower():
                        for item in section.recentlyAdded(maxresults=limit):
                            cached = self._convert_to_cached_media(item, section.title)
                            if cached:
                                results.append(cached)
                        break
            else:
                # Search all libraries - Library.recentlyAdded doesn't accept maxresults
                # so we slice the results manually
                all_recent = self.server.library.recentlyAdded()
                for item in all_recent[:limit]:
                    library_name = self._get_library_for_item(item)
                    cached = self._convert_to_cached_media(item, library_name)
                    if cached:
                        results.append(cached)
        except Exception as e:
            logger.error(f"Error fetching recently added: {e}")
        logger.debug(f"Recently added: returning {len(results)} items")
        return results

    def get_libraries(self) -> list[str]:
        """Get list of library names."""
        try:
            return [section.title for section in self.server.library.sections()]
        except Exception as e:
            logger.error(f"Error fetching libraries: {e}")
            return []

    def get_available_clients(self) -> list[PlexClient]:
        """Get list of available Plex clients."""
        clients = []
        try:
            for client in self.server.clients():
                clients.append(
                    PlexClient(
                        machine_identifier=client.machineIdentifier,
                        name=client.title,
                        device=getattr(client, "device", None),
                        platform=getattr(client, "platform", None),
                        product=getattr(client, "product", None),
                        state=getattr(client, "state", None),
                    )
                )
        except Exception as e:
            logger.error(f"Error fetching clients: {e}")
        return clients

    def generate_watch_together_link(self, rating_key: str) -> Optional[str]:
        """Generate a watch-together link for a media item."""
        try:
            item = self.server.fetchItem(int(rating_key))
            # Watch together uses Plex's web app
            server_id = self.server.machineIdentifier
            return f"https://app.plex.tv/desktop#!/server/{server_id}/details?key=%2Flibrary%2Fmetadata%2F{rating_key}&context=watch-together"
        except Exception as e:
            logger.error(f"Error generating watch-together link: {e}")
            return None

    def get_server_info(self) -> dict:
        """Get server information."""
        logger.debug("Fetching server info...")
        try:
            transcode_sessions = self.server.transcodeSessions()
            sessions = self.server.sessions()
            transcode_count = len(list(transcode_sessions)) if transcode_sessions else 0
            stream_count = len(list(sessions)) if sessions else 0
            info = {
                "name": self.server.friendlyName,
                "version": self.server.version,
                "platform": self.server.platform,
                "transcodes": transcode_count,
                "streams": stream_count,
            }
            logger.info(
                f"Server info: {info['name']} v{info['version']} "
                f"({stream_count} streams, {transcode_count} transcodes)"
            )
            return info
        except Exception as e:
            logger.error(f"Error fetching server info: {e}")
            return {}
