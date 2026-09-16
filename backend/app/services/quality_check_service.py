import os
from pathlib import Path
from typing import Optional, List
from app.schemas.dto import QualityCheckResult, QualityCheckItem
from app.models.schema import Video, VideoFile, MetadataGeneration, TitleCandidate, DescriptionRecord, TagRecord, ThumbnailRecord


class QualityCheckService:
    @staticmethod
    def evaluate(
        video: Video,
        file_info: Optional[VideoFile],
        selected_title: Optional[TitleCandidate],
        description: Optional[DescriptionRecord],
        tags: Optional[TagRecord],
        selected_thumbnail: Optional[ThumbnailRecord],
        channel_connected: bool
    ) -> QualityCheckResult:
        checks: List[QualityCheckItem] = []

        # 1. File existence
        file_exists = False
        if video.current_folder_path and os.path.exists(video.current_folder_path):
            file_exists = True
            checks.append(QualityCheckItem(
                name="File System",
                passed=True,
                status="VALID",
                message=f"Video file located: {os.path.basename(video.current_folder_path)}"
            ))
        else:
            checks.append(QualityCheckItem(
                name="File System",
                passed=False,
                status="BLOCKED",
                message="Video file not found in current local folder."
            ))

        # 2. File playable & duration
        if file_info and file_info.duration_seconds and file_info.duration_seconds > 1.0:
            checks.append(QualityCheckItem(
                name="Duration",
                passed=True,
                status="VALID",
                message=f"Valid duration: {float(file_info.duration_seconds):.1f}s"
            ))
        else:
            checks.append(QualityCheckItem(
                name="Duration",
                passed=False,
                status="BLOCKED",
                message="Media duration is missing or less than 1 second."
            ))

        # 3. Audio Presence
        if file_info and file_info.has_audio:
            checks.append(QualityCheckItem(
                name="Audio Track",
                passed=True,
                status="VALID",
                message=f"Audio detected ({file_info.audio_codec or 'PCM/AAC'})"
            ))
        else:
            checks.append(QualityCheckItem(
                name="Audio Track",
                passed=False,
                status="WARNING",
                message="No audio stream detected in video container."
            ))

        # 4. Video Codec & Resolution
        if file_info and file_info.width and file_info.height:
            is_hd = file_info.width >= 1280 or file_info.height >= 720
            status = "VALID" if is_hd else "WARNING"
            checks.append(QualityCheckItem(
                name="Resolution",
                passed=is_hd,
                status=status,
                message=f"{file_info.width}x{file_info.height} ({file_info.video_codec or 'Standard'})"
            ))
        else:
            checks.append(QualityCheckItem(
                name="Resolution",
                passed=False,
                status="WARNING",
                message="Resolution details unconfirmed."
            ))

        # 5. Title Selection
        if selected_title and selected_title.title_text:
            checks.append(QualityCheckItem(
                name="Title",
                passed=True,
                status="VALID",
                message=f"Selected: \"{selected_title.title_text[:40]}...\""
            ))
        else:
            checks.append(QualityCheckItem(
                name="Title",
                passed=False,
                status="BLOCKED",
                message="No title candidate approved or selected."
            ))

        # 6. Description
        if description and description.long_description:
            checks.append(QualityCheckItem(
                name="Description",
                passed=True,
                status="VALID",
                message="Description generated and structured."
            ))
        else:
            checks.append(QualityCheckItem(
                name="Description",
                passed=False,
                status="BLOCKED",
                message="Description is empty."
            ))

        # 7. Tags
        if tags and (tags.primary_keywords or tags.combined_tags_string):
            checks.append(QualityCheckItem(
                name="Tags",
                passed=True,
                status="VALID",
                message=f"{tags.tag_count} SEO tags generated."
            ))
        else:
            checks.append(QualityCheckItem(
                name="Tags",
                passed=False,
                status="WARNING",
                message="Tags missing or incomplete."
            ))

        # 8. Thumbnail
        if selected_thumbnail and (selected_thumbnail.local_file_path or selected_thumbnail.preview_url):
            checks.append(QualityCheckItem(
                name="Thumbnail",
                passed=True,
                status="VALID",
                message="Thumbnail selected."
            ))
        else:
            checks.append(QualityCheckItem(
                name="Thumbnail",
                passed=False,
                status="WARNING",
                message="Thumbnail not selected (YouTube will use default frame if skipped)."
            ))

        # 9. YouTube Channel Connection
        if channel_connected:
            checks.append(QualityCheckItem(
                name="Channel Connection",
                passed=True,
                status="VALID",
                message="Target YouTube channel is authenticated."
            ))
        else:
            checks.append(QualityCheckItem(
                name="Channel Connection",
                passed=False,
                status="BLOCKED",
                message="No YouTube channel connected. Connect channel in Settings."
            ))

        # Determine overall status
        has_blocked = any(c.status == "BLOCKED" for c in checks)
        has_warning = any(c.status == "WARNING" for c in checks)

        if has_blocked:
            overall = "BLOCKED"
            can_upload = False
        elif has_warning:
            overall = "WARNING"
            can_upload = True  # Can upload with warnings if approved by user
        else:
            overall = "READY"
            can_upload = True

        return QualityCheckResult(
            overall_status=overall,
            can_upload=can_upload,
            checks=checks
        )


quality_checker = QualityCheckService()
