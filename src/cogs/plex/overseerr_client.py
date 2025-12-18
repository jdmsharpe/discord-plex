import logging
from datetime import datetime
from typing import Optional
from urllib.parse import quote

import aiohttp

from .models import (
    OverseerrRequest,
    OverseerrSearchResult,
    RequestStatus,
)


logger = logging.getLogger(__name__)


class OverseerrClient:
    """Async client for Overseerr API interactions."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "X-Api-Key": self.api_key,
                    "Content-Type": "application/json",
                }
            )
        return self._session

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _request(
        self,
        method: str,
        endpoint: str,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> Optional[dict]:
        """Make an API request."""
        session = await self._get_session()
        url = f"{self.base_url}/api/v1{endpoint}"

        try:
            async with session.request(
                method, url, json=json, params=params
            ) as response:
                if response.status == 200 or response.status == 201:
                    return await response.json()
                elif response.status == 404:
                    logger.warning(f"Not found: {endpoint}")
                    return None
                else:
                    text = await response.text()
                    logger.error(f"API error {response.status}: {text}")
                    return None
        except Exception as e:
            logger.error(f"Request error for {endpoint}: {e}")
            return None

    async def search(self, query: str, page: int = 1) -> list[OverseerrSearchResult]:
        """Search for movies and TV shows."""
        results = []
        # URL-encode the query to handle special characters
        encoded_query = quote(query, safe="")
        logger.debug(f"Overseerr search: query='{query}', encoded='{encoded_query}'")
        data = await self._request(
            "GET",
            "/search",
            params={"query": encoded_query, "page": page},
        )

        if not data or "results" not in data:
            return results

        for item in data["results"]:
            media_type = item.get("mediaType")
            if media_type not in ("movie", "tv"):
                continue

            # Check if already available or requested
            media_info = item.get("mediaInfo")
            already_available = False
            already_requested = False
            request_status = None

            if media_info:
                status = media_info.get("status")
                if status == 5:  # Available
                    already_available = True
                elif status in (2, 3, 4):  # Pending, Processing, Partially Available
                    already_requested = True
                    request_status = self._convert_status(status)

            title = item.get("title") if media_type == "movie" else item.get("name")
            release_date = (
                item.get("releaseDate")
                if media_type == "movie"
                else item.get("firstAirDate")
            )
            year = None
            if release_date:
                try:
                    year = int(release_date[:4])
                except (ValueError, IndexError):
                    pass

            results.append(
                OverseerrSearchResult(
                    media_type=media_type,
                    tmdb_id=item.get("id"),
                    title=title or "Unknown",
                    year=year,
                    poster_path=item.get("posterPath"),
                    overview=item.get("overview"),
                    vote_average=item.get("voteAverage"),
                    already_available=already_available,
                    already_requested=already_requested,
                    request_status=request_status,
                )
            )

        return results

    @staticmethod
    def _convert_status(status: int) -> RequestStatus:
        """Convert Overseerr status code to RequestStatus."""
        status_map = {
            1: RequestStatus.PENDING,
            2: RequestStatus.APPROVED,
            3: RequestStatus.DECLINED,
            4: RequestStatus.PROCESSING,
            5: RequestStatus.AVAILABLE,
        }
        return status_map.get(status, RequestStatus.UNKNOWN)

    async def get_request(self, request_id: int) -> Optional[OverseerrRequest]:
        """Get a specific request by ID."""
        data = await self._request("GET", f"/request/{request_id}")
        if not data:
            return None
        return self._parse_request(data)

    async def get_user_requests(
        self,
        user_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> list[OverseerrRequest]:
        """Get requests, optionally filtered by user or status."""
        params = {}
        if status:
            params["filter"] = status

        # If user_id specified, we filter client-side as Overseerr
        # doesn't have a direct user filter endpoint for all requests
        data = await self._request("GET", "/request", params=params)

        if not data or "results" not in data:
            return []

        requests = []
        for item in data["results"]:
            req = self._parse_request(item)
            if req:
                if user_id is None or (
                    req.requested_by and str(user_id) in req.requested_by
                ):
                    requests.append(req)

        return requests

    async def get_pending_requests(self) -> list[OverseerrRequest]:
        """Get all pending requests (for admin view)."""
        return await self.get_user_requests(status="pending")

    def _parse_request(self, data: dict) -> Optional[OverseerrRequest]:
        """Parse request data into OverseerrRequest."""
        try:
            media = data.get("media", {})
            requested_by = data.get("requestedBy", {})

            media_type = media.get("mediaType", "movie")
            tmdb_id = media.get("tmdbId", 0)

            # Get title from media info
            title = "Unknown"
            year = None
            poster_path = None
            overview = None

            # Try to get extra info if available
            if "title" in media:
                title = media["title"]
            if "releaseDate" in media:
                try:
                    year = int(media["releaseDate"][:4])
                except (ValueError, IndexError, TypeError):
                    pass
            if "posterPath" in media:
                poster_path = media["posterPath"]

            # Parse status
            status = self._convert_status(data.get("status", 1))

            # Parse date
            created_at = data.get("createdAt")
            requested_at = datetime.now()
            if created_at:
                try:
                    requested_at = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                except ValueError:
                    pass

            return OverseerrRequest(
                request_id=data.get("id", 0),
                media_type=media_type,
                tmdb_id=tmdb_id,
                title=title,
                year=year,
                status=status,
                requested_by=requested_by.get("displayName")
                or requested_by.get("email")
                or "Unknown",
                requested_at=requested_at,
                poster_path=poster_path,
                overview=overview,
            )
        except Exception as e:
            logger.warning(f"Error parsing request: {e}")
            return None

    async def create_request(
        self,
        media_type: str,
        tmdb_id: int,
        seasons: Optional[list[int]] = None,
    ) -> Optional[OverseerrRequest]:
        """Create a new media request."""
        endpoint = "/request"
        payload = {
            "mediaType": media_type,
            "mediaId": tmdb_id,
        }

        if media_type == "tv" and seasons:
            payload["seasons"] = seasons

        logger.info(f"Creating Overseerr request: type={media_type}, tmdb_id={tmdb_id}")
        data = await self._request("POST", endpoint, json=payload)
        if not data:
            logger.error(f"Overseerr request creation failed: type={media_type}, tmdb_id={tmdb_id}")
            return None

        request = self._parse_request(data)
        if request:
            logger.info(f"Overseerr request created: id={request.request_id}, status={request.status.value}")
        return request

    async def approve_request(self, request_id: int) -> bool:
        """Approve a pending request."""
        logger.info(f"Approving Overseerr request: id={request_id}")
        data = await self._request("POST", f"/request/{request_id}/approve")
        success = data is not None
        if success:
            logger.info(f"Overseerr request {request_id} approved successfully")
        else:
            logger.error(f"Failed to approve Overseerr request {request_id}")
        return success

    async def decline_request(self, request_id: int) -> bool:
        """Decline a pending request."""
        logger.info(f"Declining Overseerr request: id={request_id}")
        data = await self._request("POST", f"/request/{request_id}/decline")
        success = data is not None
        if success:
            logger.info(f"Overseerr request {request_id} declined successfully")
        else:
            logger.error(f"Failed to decline Overseerr request {request_id}")
        return success

    async def delete_request(self, request_id: int) -> bool:
        """Delete a request."""
        session = await self._get_session()
        url = f"{self.base_url}/api/v1/request/{request_id}"

        try:
            async with session.delete(url) as response:
                return response.status == 204
        except Exception as e:
            logger.error(f"Error deleting request: {e}")
            return False

    async def get_media_details(
        self,
        media_type: str,
        tmdb_id: int,
    ) -> Optional[dict]:
        """Get detailed media info from Overseerr/TMDB."""
        endpoint = f"/{media_type}/{tmdb_id}"
        return await self._request("GET", endpoint)

    async def get_poster_url(
        self,
        media_type: str,
        tmdb_id: int,
    ) -> Optional[str]:
        """Get TMDB poster URL for a media item."""
        details = await self.get_media_details(media_type, tmdb_id)
        if details and details.get("posterPath"):
            return f"https://image.tmdb.org/t/p/w500{details['posterPath']}"
        return None

    async def get_users(self) -> list[dict]:
        """Get list of Overseerr users."""
        data = await self._request("GET", "/user", params={"take": 100})
        if not data or "results" not in data:
            return []
        return data["results"]

    async def get_user_by_plex_id(self, plex_id: int) -> Optional[dict]:
        """Find an Overseerr user by their Plex ID."""
        users = await self.get_users()
        for user in users:
            if user.get("plexId") == plex_id:
                return user
        return None

    async def get_status(self) -> Optional[dict]:
        """Get Overseerr server status."""
        return await self._request("GET", "/status")
