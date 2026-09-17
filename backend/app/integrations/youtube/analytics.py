"""
YouTube Analytics API Client — Fetches channel and video metrics
from the YouTube Analytics and Reporting API. Supports time-range
filtering (today, 7d, 28d, 90d, lifetime) and per-video breakdowns.
"""
import httpx
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from app.core.logging import system_logger


class YouTubeAnalyticsClient:
    """Client for YouTube Analytics and Reporting API."""

    ANALYTICS_URL = "https://youtubeanalytics.googleapis.com/v2/reports"
    DATA_API_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}

    async def get_channel_metrics(
        self, channel_id: str, timeframe: str = "28d"
    ) -> Dict[str, Any]:
        """
        Fetch aggregate channel metrics for a given timeframe.

        Args:
            channel_id: YouTube channel ID.
            timeframe: One of 'today', '7d', '28d', '90d', 'lifetime'.

        Returns:
            Dict with views, watch_time_hours, subscribers_gained, likes,
            comments, average_view_duration, estimated_revenue, etc.
        """
        start_date, end_date = self._resolve_date_range(timeframe)

        params = {
            "ids": f"channel=={channel_id}",
            "startDate": start_date,
            "endDate": end_date,
            "metrics": ",".join([
                "views", "estimatedMinutesWatched", "averageViewDuration",
                "subscribersGained", "subscribersLost", "likes", "dislikes",
                "comments", "shares", "annotationClickThroughRate",
            ]),
            "dimensions": "",
        }

        data = await self._query(params)
        if not data or not data.get("rows"):
            return self._empty_channel_metrics(timeframe)

        row = data["rows"][0]
        headers = [col["name"] for col in data.get("columnHeaders", [])]
        metrics = dict(zip(headers, row))

        return {
            "timeframe": timeframe,
            "start_date": start_date,
            "end_date": end_date,
            "views": metrics.get("views", 0),
            "watch_time_hours": round(metrics.get("estimatedMinutesWatched", 0) / 60, 1),
            "average_view_duration_seconds": metrics.get("averageViewDuration", 0),
            "subscribers_gained": metrics.get("subscribersGained", 0),
            "subscribers_lost": metrics.get("subscribersLost", 0),
            "net_subscribers": metrics.get("subscribersGained", 0) - metrics.get("subscribersLost", 0),
            "likes": metrics.get("likes", 0),
            "dislikes": metrics.get("dislikes", 0),
            "comments": metrics.get("comments", 0),
            "shares": metrics.get("shares", 0),
        }

    async def get_daily_views(
        self, channel_id: str, timeframe: str = "28d"
    ) -> List[Dict[str, Any]]:
        """
        Fetch daily view counts for charting.

        Returns:
            List of {date, views, watch_time_minutes, subscribers_gained}.
        """
        start_date, end_date = self._resolve_date_range(timeframe)

        params = {
            "ids": f"channel=={channel_id}",
            "startDate": start_date,
            "endDate": end_date,
            "metrics": "views,estimatedMinutesWatched,subscribersGained",
            "dimensions": "day",
            "sort": "day",
        }

        data = await self._query(params)
        if not data or not data.get("rows"):
            return []

        return [
            {
                "date": row[0],
                "views": row[1],
                "watch_time_minutes": row[2],
                "subscribers_gained": row[3],
            }
            for row in data["rows"]
        ]

    async def get_top_videos(
        self, channel_id: str, timeframe: str = "28d", max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch top-performing videos by views for a given timeframe.

        Returns:
            List of {video_id, views, watch_time_minutes, likes, comments, average_view_duration}.
        """
        start_date, end_date = self._resolve_date_range(timeframe)

        params = {
            "ids": f"channel=={channel_id}",
            "startDate": start_date,
            "endDate": end_date,
            "metrics": "views,estimatedMinutesWatched,likes,comments,averageViewDuration",
            "dimensions": "video",
            "sort": "-views",
            "maxResults": str(max_results),
        }

        data = await self._query(params)
        if not data or not data.get("rows"):
            return []

        return [
            {
                "video_id": row[0],
                "views": row[1],
                "watch_time_minutes": row[2],
                "likes": row[3],
                "comments": row[4],
                "average_view_duration": row[5],
            }
            for row in data["rows"]
        ]

    async def get_video_metrics(
        self, channel_id: str, video_id: str, timeframe: str = "lifetime"
    ) -> Dict[str, Any]:
        """Fetch detailed metrics for a specific video."""
        start_date, end_date = self._resolve_date_range(timeframe)

        params = {
            "ids": f"channel=={channel_id}",
            "startDate": start_date,
            "endDate": end_date,
            "metrics": ",".join([
                "views", "estimatedMinutesWatched", "averageViewDuration",
                "likes", "dislikes", "comments", "shares",
                "subscribersGained", "subscribersLost",
                "annotationClickThroughRate",
            ]),
            "filters": f"video=={video_id}",
        }

        data = await self._query(params)
        if not data or not data.get("rows"):
            return {"video_id": video_id, "timeframe": timeframe, "views": 0}

        row = data["rows"][0]
        headers = [col["name"] for col in data.get("columnHeaders", [])]
        metrics = dict(zip(headers, row))

        return {
            "video_id": video_id,
            "timeframe": timeframe,
            "views": metrics.get("views", 0),
            "watch_time_hours": round(metrics.get("estimatedMinutesWatched", 0) / 60, 1),
            "average_view_duration_seconds": metrics.get("averageViewDuration", 0),
            "likes": metrics.get("likes", 0),
            "dislikes": metrics.get("dislikes", 0),
            "comments": metrics.get("comments", 0),
            "shares": metrics.get("shares", 0),
            "subscribers_gained": metrics.get("subscribersGained", 0),
        }

    async def get_traffic_sources(
        self, channel_id: str, timeframe: str = "28d"
    ) -> List[Dict[str, Any]]:
        """Fetch traffic source breakdown."""
        start_date, end_date = self._resolve_date_range(timeframe)

        params = {
            "ids": f"channel=={channel_id}",
            "startDate": start_date,
            "endDate": end_date,
            "metrics": "views,estimatedMinutesWatched",
            "dimensions": "insightTrafficSourceType",
            "sort": "-views",
        }

        data = await self._query(params)
        if not data or not data.get("rows"):
            return []

        return [
            {
                "source": row[0],
                "views": row[1],
                "watch_time_minutes": row[2],
            }
            for row in data["rows"]
        ]

    async def get_demographics(
        self, channel_id: str, timeframe: str = "28d"
    ) -> Dict[str, Any]:
        """Fetch viewer demographics (age group and gender)."""
        start_date, end_date = self._resolve_date_range(timeframe)

        params = {
            "ids": f"channel=={channel_id}",
            "startDate": start_date,
            "endDate": end_date,
            "metrics": "viewerPercentage",
            "dimensions": "ageGroup,gender",
        }

        data = await self._query(params)
        if not data or not data.get("rows"):
            return {"age_groups": [], "genders": []}

        demographics = []
        for row in data["rows"]:
            demographics.append({
                "age_group": row[0],
                "gender": row[1],
                "viewer_percentage": row[2],
            })

        return {"demographics": demographics}

    async def _query(self, params: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Execute a YouTube Analytics API query."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(
                    self.ANALYTICS_URL, params=params, headers=self.headers
                )
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 401:
                    system_logger.error("YouTube Analytics: Access token expired")
                elif resp.status_code == 403:
                    system_logger.error(f"YouTube Analytics: Forbidden — {resp.text}")
                else:
                    system_logger.error(
                        f"YouTube Analytics query failed ({resp.status_code}): {resp.text}"
                    )
            except Exception as e:
                system_logger.error(f"YouTube Analytics request error: {e}")
        return None

    @staticmethod
    def _resolve_date_range(timeframe: str) -> tuple:
        """Convert a timeframe string to (start_date, end_date) in YYYY-MM-DD format."""
        today = datetime.utcnow().date()

        if timeframe == "today":
            return str(today), str(today)
        elif timeframe == "7d":
            return str(today - timedelta(days=7)), str(today)
        elif timeframe == "28d":
            return str(today - timedelta(days=28)), str(today)
        elif timeframe == "90d":
            return str(today - timedelta(days=90)), str(today)
        elif timeframe == "lifetime":
            # YouTube channels can be very old; use a wide range
            return "2005-01-01", str(today)
        else:
            # Default to 28 days
            return str(today - timedelta(days=28)), str(today)

    @staticmethod
    def _empty_channel_metrics(timeframe: str) -> Dict[str, Any]:
        """Return zeroed-out metrics structure."""
        return {
            "timeframe": timeframe,
            "views": 0,
            "watch_time_hours": 0,
            "average_view_duration_seconds": 0,
            "subscribers_gained": 0,
            "subscribers_lost": 0,
            "net_subscribers": 0,
            "likes": 0,
            "dislikes": 0,
            "comments": 0,
            "shares": 0,
        }
