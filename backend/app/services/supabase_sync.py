import os
import sys
import json
import base64
import hashlib
import threading
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from cryptography.fernet import Fernet
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from supabase import create_client, Client

from app.core.config import settings
from app.core import user_settings
from app.core.database import AsyncSessionLocal
from app.core.logging import system_logger
from app.models.schema import (
    Channel, YouTubeConnection, Video, VideoFile, VideoAnalysis,
    Transcript, MetadataGeneration, TitleCandidate, DescriptionRecord,
    TagRecord, ThumbnailRecord, Notification
)

_last_sync_time = 0.0
_SYNC_THROTTLE_SECONDS = 5.0
# Single-flight guard: the sync is triggered from request handlers (main event
# loop) AND the ingest daemon thread (its own asyncio.run loop). Without this,
# concurrent runs race and collide on INSERT (UNIQUE constraint on videos.id).
_sync_lock = threading.Lock()


def _get_supabase_client() -> Optional[Client]:
    if not (settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY):
        return None
    try:
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    except Exception as e:
        system_logger.error(f"Failed to create Supabase client: {e}")
        return None


def _get_youtube_access_token(cred: Dict[str, Any]) -> Optional[str]:
    """Decrypt Google refresh token from Supabase and mint an access token."""
    try:
        encrypted = cred.get("refresh_token_encrypted")
        if not encrypted or not settings.WORKER_SECRET_KEY:
            return None
        key_bytes = hashlib.sha256(settings.WORKER_SECRET_KEY.encode()).digest()
        refresh_token = Fernet(base64.urlsafe_b64encode(key_bytes)).decrypt(
            encrypted.encode()
        ).decode()

        resp = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=15.0,
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
    except Exception as e:
        system_logger.warning(f"Error minting YouTube access token: {e}")
    return None


async def sync_channel_from_cloud(db: AsyncSession) -> Optional[Channel]:
    """Fetch YouTube channel info from Supabase worker_credentials and live YouTube API."""
    client = _get_supabase_client()
    if not client:
        return None

    try:
        res = client.table("worker_credentials").select("*").eq("id", "google").limit(1).execute()
        rows = res.data or []
        if not rows:
            return None
        cred = rows[0]
        ch_id = cred.get("youtube_channel_id")
        if not ch_id:
            return None

        title = cred.get("youtube_channel_title") or "YouTube Channel"
        custom_url = None
        thumbnail_url = None
        subscribers = 0
        views = 0
        videos = 0

        # Try live YouTube Data API fetch for up-to-date stats
        access_token = _get_youtube_access_token(cred)
        if access_token:
            try:
                ch_resp = httpx.get(
                    "https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&mine=true",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=10.0,
                )
                if ch_resp.status_code == 200:
                    items = ch_resp.json().get("items", [])
                    if items:
                        item = items[0]
                        ch_id = item.get("id") or ch_id
                        snippet = item.get("snippet", {})
                        stats = item.get("statistics", {})
                        title = snippet.get("title") or title
                        custom_url = snippet.get("customUrl")
                        thumbs = snippet.get("thumbnails", {})
                        thumbnail_url = (
                            thumbs.get("high", {}).get("url")
                            or thumbs.get("medium", {}).get("url")
                            or thumbs.get("default", {}).get("url")
                        )
                        subscribers = int(stats.get("subscriberCount", 0))
                        views = int(stats.get("viewCount", 0))
                        videos = int(stats.get("videoCount", 0))
            except Exception as e:
                system_logger.warning(f"Failed to fetch live YouTube channel details: {e}")

        # Check existing channel in local SQLite
        q = await db.execute(select(Channel).where(Channel.youtube_channel_id == ch_id))
        channel = q.scalar_one_or_none()

        if not channel:
            channel = Channel(
                youtube_channel_id=ch_id,
                title=title,
                custom_url=custom_url,
                thumbnail_url=thumbnail_url,
                subscriber_count=subscribers,
                view_count=views,
                video_count=videos,
                is_active=True,
            )
            db.add(channel)
        else:
            channel.title = title
            if custom_url:
                channel.custom_url = custom_url
            if thumbnail_url:
                channel.thumbnail_url = thumbnail_url
            channel.subscriber_count = subscribers
            channel.view_count = views
            channel.video_count = videos
            channel.is_active = True

        await db.commit()
        return channel
    except Exception as e:
        system_logger.error(f"Error syncing channel from cloud: {e}")
        return None


def _probe_video_file(file_path: Optional[str]) -> Dict[str, Any]:
    """Run ffprobe on target file to extract accurate duration, streams, and resolution."""
    info = {
        "duration": 0.0,
        "width": None,
        "height": None,
        "video_codec": None,
        "audio_codec": None,
        "has_audio": True,
        "file_size": 0,
    }
    if not file_path or not os.path.exists(file_path):
        return info
    info["file_size"] = os.path.getsize(file_path)
    try:
        import subprocess
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", file_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True, creationflags=creation_flags)
        p_data = json.loads(res.stdout)
        info["duration"] = float(p_data.get("format", {}).get("duration", 0.0))
        v_stream = next((s for s in p_data.get("streams", []) if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in p_data.get("streams", []) if s.get("codec_type") == "audio"), None)
        if v_stream:
            info["width"] = v_stream.get("width")
            info["height"] = v_stream.get("height")
            info["video_codec"] = v_stream.get("codec_name")
        if a_stream:
            info["audio_codec"] = a_stream.get("codec_name")
            info["has_audio"] = True
    except Exception as e:
        system_logger.warning(f"ffprobe probe failed for {file_path}: {e}")
    return info


def _find_local_file(file_name: str, given_path: Optional[str] = None) -> Optional[str]:
    """Resolve the physical location of the video on the user's computer."""
    candidates = []
    if given_path and os.path.exists(given_path) and os.path.isfile(given_path):
        return given_path

    custom_folder = user_settings.get("custom_upload_folder") or "C:\\Users\\asus\\Downloads\\YouTube"
    if custom_folder and os.path.isdir(custom_folder):
        candidates.append(os.path.join(custom_folder, file_name))
        # Fuzzy match prefix in case filename was slightly altered
        clean_prefix = file_name.split(".")[0].split("-")[0].split("_")[0]
        try:
            for f in os.listdir(custom_folder):
                if len(clean_prefix) >= 3 and f.lower().startswith(clean_prefix.lower()):
                    candidates.append(os.path.join(custom_folder, f))
        except Exception:
            pass

    for c in candidates:
        if c and os.path.exists(c) and os.path.isfile(c):
            return c
    return None


def _extract_video_thumbnail(video_path: Optional[str], video_id: str) -> Optional[str]:
    """Extract a representative 1280x720 frame from the video using ffmpeg."""
    try:
        if not video_path or not os.path.exists(video_path):
            return None
        thumbs_dir = os.path.join("data", "thumbnails")
        os.makedirs(thumbs_dir, exist_ok=True)
        out_thumb = os.path.join(thumbs_dir, f"{video_id}_thumb.jpg")
        if os.path.exists(out_thumb) and os.path.getsize(out_thumb) > 1000:
            return out_thumb
        import subprocess
        creation_flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        cmd = [
            "ffmpeg", "-y", "-ss", "00:00:02", "-i", video_path,
            "-vframes", "1", "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
            out_thumb
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10, creationflags=creation_flags)
        if res.returncode == 0 and os.path.exists(out_thumb):
            return out_thumb
    except Exception as e:
        system_logger.warning(f"Failed to generate thumbnail frame: {e}")
    return None


async def sync_videos_from_cloud(db: AsyncSession) -> int:
    """Synchronize ingest_items from Supabase into local Video rows with media inspection."""
    client = _get_supabase_client()
    if not client:
        return 0

    synced_count = 0
    try:
        res = client.table("ingest_items").select("*").execute()
        items = res.data or []

        # Find default active channel if any
        ch_q = await db.execute(select(Channel).where(Channel.is_active == True))
        active_channel = ch_q.scalar_one_or_none()
        channel_id = active_channel.id if active_channel else None

        for item in items:
            item_id = item["id"]
            file_name = item.get("file_name") or "video.mp4"
            status_raw = (item.get("status") or "QUEUED").upper()

            # Map to Studio video status
            if status_raw == "UPLOADED":
                status = "UPLOADED"
            elif status_raw == "PROCESSING":
                status = "PROCESSING"
            elif status_raw == "FAILED":
                status = "FAILED"
            else:
                status = "APPROVED"

            ai_meta = item.get("ai_metadata") or {}
            sha256_hash = item.get("sha256") or ""
            local_path = item.get("local_path") or ""

            # Locate local file and probe media format with ffprobe
            real_path = _find_local_file(file_name, local_path)
            probe = _probe_video_file(real_path)
            actual_duration = probe.get("duration") or 0.0
            actual_size = probe.get("file_size") or item.get("size_bytes") or 0

            # Derive title
            clean_base = os.path.splitext(os.path.basename(real_path or file_name))[0]
            clean_title = clean_base.replace("_", " ").replace("-", " ").title()
            title = ai_meta.get("title") or clean_title

            # Check if video exists by id or filename
            v_q = await db.execute(select(Video).where(Video.id == item_id))
            video = v_q.scalar_one_or_none()

            if not video:
                fn_q = await db.execute(select(Video).where(Video.original_filename == file_name))
                video = fn_q.scalar_one_or_none()

            if not video:
                uploaded_at_val = None
                if status == "UPLOADED" and item.get("updated_at"):
                    try:
                        uploaded_at_val = datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00"))
                    except Exception:
                        uploaded_at_val = datetime.now(timezone.utc)

                video = Video(
                    id=item_id,
                    channel_id=channel_id,
                    title=title,
                    status=status,
                    publishing_mode="APPROVAL_REQUIRED",
                    quality_status="READY" if (status == "UPLOADED" or actual_duration > 1.0) else "PENDING",
                    source_path=real_path or local_path,
                    current_folder_path=real_path or local_path,
                    original_filename=file_name,
                    youtube_video_id=item.get("youtube_video_id"),
                    youtube_url=item.get("youtube_url"),
                    uploaded_at=uploaded_at_val,
                )
                db.add(video)
                await db.flush()

                # Create VideoFile entry
                vf = VideoFile(
                    video_id=video.id,
                    sha256_hash=sha256_hash,
                    file_size_bytes=actual_size,
                    duration_seconds=actual_duration,
                    width=probe.get("width"),
                    height=probe.get("height"),
                    video_codec=probe.get("video_codec"),
                    audio_codec=probe.get("audio_codec"),
                    has_audio=probe.get("has_audio", True),
                )
                db.add(vf)

                # Create Transcript if available
                if item.get("transcript"):
                    tr = Transcript(
                        video_id=video.id,
                        full_text=item["transcript"],
                    )
                    db.add(tr)

                # Metadata & Title generation
                desc_text = (
                    ai_meta.get("description")
                    or f"High-quality 4K video showcase of {clean_title}.\n\nEnhanced dynamic range, smooth motion, and rich color fidelity.\n\n#4K #HDR #Cinematic #Showcase"
                )
                tags_list = ai_meta.get("tags") or ["4K", "HDR", "High Bitrate", "Cinematic", "Showcase", "Ultra HD"]
                summary_text = ai_meta.get("summary") or f"Showcase video of {clean_title}."

                va = VideoAnalysis(
                    video_id=video.id,
                    summary=summary_text,
                    topics=tags_list[:3],
                    keywords=tags_list,
                )
                db.add(va)

                mg = MetadataGeneration(
                    video_id=video.id,
                    version_number=1,
                    ai_provider=settings.DEFAULT_AI_PROVIDER,
                    model_name="default",
                    is_active=True,
                )
                db.add(mg)
                await db.flush()

                # Generate 5 title candidates
                candidates = [
                    f"{clean_title} - 4K Quality Showcase",
                    f"Ultra High Bitrate Demo: {clean_title}",
                    f"{clean_title} (Cinematic 4K HDR)",
                    f"Visual Performance Test: {clean_title}",
                    f"The Ultimate {clean_title} Experience",
                ]
                for idx, c_text in enumerate(candidates):
                    tc = TitleCandidate(
                        metadata_generation_id=mg.id,
                        title_text=c_text,
                        is_selected=(idx == 0),
                        candidate_index=idx + 1,
                    )
                    db.add(tc)

                dr = DescriptionRecord(
                    metadata_generation_id=mg.id,
                    short_description=summary_text[:200],
                    long_description=desc_text,
                )
                db.add(dr)

                tr_record = TagRecord(
                    metadata_generation_id=mg.id,
                    primary_keywords=tags_list,
                    combined_tags_string=", ".join(tags_list),
                    tag_count=len(tags_list),
                )
                db.add(tr_record)

                # Thumbnail record
                thumb_path = _extract_video_thumbnail(real_path, video.id) if real_path else None
                thumb = ThumbnailRecord(
                    video_id=video.id,
                    metadata_generation_id=mg.id,
                    concept_title=f"{clean_title} Hero Frame",
                    local_file_path=thumb_path,
                    preview_url=f"/data/thumbnails/{os.path.basename(thumb_path)}" if thumb_path else None,
                    status="READY" if thumb_path else "DRAFT",
                    is_selected=True,
                )
                db.add(thumb)

                synced_count += 1
            else:
                # Update existing video
                video.status = status
                if real_path:
                    video.source_path = real_path
                    video.current_folder_path = real_path
                if item.get("youtube_video_id"):
                    video.youtube_video_id = item["youtube_video_id"]
                if item.get("youtube_url"):
                    video.youtube_url = item["youtube_url"]

                # Ensure VideoFile has real duration and dimensions
                vf_q = await db.execute(select(VideoFile).where(VideoFile.video_id == video.id))
                vf = vf_q.scalar_one_or_none()
                if not vf:
                    vf = VideoFile(
                        video_id=video.id,
                        sha256_hash=sha256_hash,
                        file_size_bytes=actual_size,
                        duration_seconds=actual_duration,
                        width=probe.get("width"),
                        height=probe.get("height"),
                        video_codec=probe.get("video_codec"),
                        audio_codec=probe.get("audio_codec"),
                        has_audio=probe.get("has_audio", True),
                    )
                    db.add(vf)
                else:
                    if (not vf.duration_seconds or float(vf.duration_seconds) <= 1.0) and actual_duration > 0:
                        vf.duration_seconds = actual_duration
                    if not vf.width and probe.get("width"):
                        vf.width = probe.get("width")
                    if not vf.height and probe.get("height"):
                        vf.height = probe.get("height")
                    if probe.get("video_codec"):
                        vf.video_codec = probe.get("video_codec")
                    if probe.get("audio_codec"):
                        vf.audio_codec = probe.get("audio_codec")
                    if actual_size > 0 and (not vf.file_size_bytes or vf.file_size_bytes == 0):
                        vf.file_size_bytes = actual_size

                # Ensure title candidates and description exist
                desc_text = (
                    ai_meta.get("description")
                    or f"High-quality 4K video showcase of {clean_title}.\n\nEnhanced dynamic range, smooth motion, and rich color fidelity.\n\n#4K #HDR #Cinematic #Showcase"
                )
                tags_list = ai_meta.get("tags") or ["4K", "HDR", "High Bitrate", "Cinematic", "Showcase"]
                summary_text = ai_meta.get("summary") or f"Showcase video of {clean_title}."

                mg_q = await db.execute(
                    select(MetadataGeneration)
                    .where(MetadataGeneration.video_id == video.id)
                    .order_by(MetadataGeneration.is_active.desc(), MetadataGeneration.version_number.desc())
                )
                mg = mg_q.scalars().first()
                if not mg:
                    mg = MetadataGeneration(
                        video_id=video.id,
                        version_number=1,
                        ai_provider=settings.DEFAULT_AI_PROVIDER,
                        model_name="default",
                        is_active=True,
                    )
                    db.add(mg)
                    await db.flush()

                # Ensure 5 title candidates exist and at least one is selected
                tc_q = await db.execute(select(TitleCandidate).where(TitleCandidate.metadata_generation_id == mg.id))
                titles = tc_q.scalars().all()
                if not titles:
                    candidates = [
                        f"{clean_title} - 4K Quality Showcase",
                        f"Ultra High Bitrate Demo: {clean_title}",
                        f"{clean_title} (Cinematic 4K HDR)",
                        f"Visual Performance Test: {clean_title}",
                        f"The Ultimate {clean_title} Experience",
                    ]
                    for idx, c_text in enumerate(candidates):
                        tc = TitleCandidate(
                            metadata_generation_id=mg.id,
                            title_text=c_text,
                            is_selected=(idx == 0),
                            candidate_index=idx + 1,
                        )
                        db.add(tc)
                elif not any(t.is_selected for t in titles):
                    titles[0].is_selected = True

                # Ensure description exists
                dr_q = await db.execute(select(DescriptionRecord).where(DescriptionRecord.metadata_generation_id == mg.id))
                dr = dr_q.scalar_one_or_none()
                if not dr:
                    dr = DescriptionRecord(
                        metadata_generation_id=mg.id,
                        short_description=summary_text[:200],
                        long_description=desc_text,
                    )
                    db.add(dr)

                # Ensure tags exist
                tr_q = await db.execute(select(TagRecord).where(TagRecord.metadata_generation_id == mg.id))
                tr_record = tr_q.scalar_one_or_none()
                if not tr_record:
                    tr_record = TagRecord(
                        metadata_generation_id=mg.id,
                        primary_keywords=tags_list,
                        combined_tags_string=", ".join(tags_list),
                        tag_count=len(tags_list),
                    )
                    db.add(tr_record)

                # Ensure ThumbnailRecord exists and has a frame
                thumb_q = await db.execute(
                    select(ThumbnailRecord)
                    .where(ThumbnailRecord.video_id == video.id)
                    .order_by(ThumbnailRecord.is_selected.desc())
                )
                thumb = thumb_q.scalars().first()
                thumb_path = _extract_video_thumbnail(real_path, video.id) if real_path else None
                if not thumb:
                    thumb = ThumbnailRecord(
                        video_id=video.id,
                        metadata_generation_id=mg.id,
                        concept_title=f"{clean_title} Hero Frame",
                        local_file_path=thumb_path,
                        preview_url=f"/data/thumbnails/{os.path.basename(thumb_path)}" if thumb_path else None,
                        status="READY" if thumb_path else "DRAFT",
                        is_selected=True,
                    )
                    db.add(thumb)
                elif thumb_path and not thumb.local_file_path:
                    thumb.local_file_path = thumb_path
                    thumb.preview_url = f"/data/thumbnails/{os.path.basename(thumb_path)}"
                    thumb.status = "READY"
                    thumb.is_selected = True

                if (vf and vf.duration_seconds and float(vf.duration_seconds) > 1.0) or actual_duration > 1.0:
                    video.quality_status = "READY"

                synced_count += 1

        await db.commit()
    except Exception as e:
        system_logger.error(f"Error syncing videos from cloud: {e}")

    return synced_count


async def sync_all_from_cloud(force: bool = False) -> None:
    """Run full cloud-to-SQLite sync — throttled and single-flight.

    Skips immediately if another sync is already in progress (across threads),
    which prevents the concurrent-insert race that collided on videos.id.
    """
    global _last_sync_time
    import time
    now = time.time()
    if not force and (now - _last_sync_time < _SYNC_THROTTLE_SECONDS):
        return

    # Non-blocking: if a sync is already running, let this call go — the running
    # one will pick up the same data.
    if not _sync_lock.acquire(blocking=False):
        return
    try:
        _last_sync_time = now
        async with AsyncSessionLocal() as db:
            try:
                await sync_channel_from_cloud(db)
                await sync_videos_from_cloud(db)
            except Exception as e:
                try:
                    await db.rollback()
                except Exception:
                    pass
                system_logger.error(f"Full cloud sync failed: {e}")
    finally:
        _sync_lock.release()
