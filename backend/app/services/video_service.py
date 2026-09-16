import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.logging import system_logger, agent_logger
from app.models.schema import (
    Video, VideoFile, VideoAnalysis, Transcript,
    MetadataGeneration, TitleCandidate, DescriptionRecord,
    TagRecord, ThumbnailRecord, UploadJob, Notification, Job
)
from app.integrations.ai.factory import ai_factory
from app.services.quality_check_service import quality_checker


class VideoService:
    @staticmethod
    async def register_detected_video(
        db: AsyncSession,
        source_path: str,
        sha256_hash: str,
        file_size: int,
        duration: float,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[float] = None,
        video_codec: Optional[str] = None,
        audio_codec: Optional[str] = None,
        has_audio: bool = True
    ) -> Dict[str, Any]:
        """Process a newly detected video file with SHA-256 duplicate prevention."""
        # 1. Duplicate detection
        existing_file_q = await db.execute(
            select(VideoFile).where(VideoFile.sha256_hash == sha256_hash)
        )
        existing_file = existing_file_q.scalar_one_or_none()
        if existing_file:
            system_logger.warning(f"Duplicate video detected with hash {sha256_hash}")
            return {
                "success": False,
                "is_duplicate": True,
                "message": "Duplicate video detected: A video with the identical SHA-256 signature already exists in the studio library."
            }

        filename = os.path.basename(source_path)
        base_title = os.path.splitext(filename)[0].replace("_", " ").replace("-", " ").title()

        # 2. Move file from INBOX to PROCESSING directory
        settings.ensure_directories()
        processing_dest = settings.processing_path / filename
        try:
            if os.path.exists(source_path) and Path(source_path).resolve() != processing_dest.resolve():
                shutil.move(source_path, str(processing_dest))
                current_path = str(processing_dest)
            else:
                current_path = source_path
        except Exception as e:
            agent_logger.error(f"Error moving video to PROCESSING folder: {e}")
            current_path = source_path

        # 3. Create Video entity
        video = Video(
            title=base_title,
            status="PROCESSING",
            publishing_mode="APPROVAL_REQUIRED",
            quality_status="PENDING",
            source_path=source_path,
            current_folder_path=current_path,
            original_filename=filename,
            active_metadata_version=1
        )
        db.add(video)
        await db.flush()

        # 4. Create VideoFile technical metadata entity
        video_file = VideoFile(
            video_id=video.id,
            sha256_hash=sha256_hash,
            file_size_bytes=file_size,
            duration_seconds=duration,
            width=width,
            height=height,
            fps=fps,
            video_codec=video_codec,
            audio_codec=audio_codec,
            has_audio=has_audio,
            container_format=os.path.splitext(filename)[1].lstrip(".").lower()
        )
        db.add(video_file)

        # 5. Create In-App Notification
        notification = Notification(
            title="New Video Detected",
            message=f"Ingested '{filename}' ({float(duration):.1f}s). Initializing AI analysis pipeline.",
            notification_type="NEW_VIDEO_DETECTED",
            severity="INFO",
            deep_link=f"/videos/{video.id}"
        )
        db.add(notification)

        # 6. Create Job record
        job = Job(
            job_type="VIDEO_ANALYSIS",
            resource_id=video.id,
            status="PENDING",
            payload={"source_path": current_path, "filename": filename}
        )
        db.add(job)

        await db.commit()
        system_logger.info(f"Registered video '{video.title}' (ID: {video.id})")
        return {"success": True, "video_id": video.id, "title": video.title}

    @staticmethod
    async def run_ai_pipeline(db: AsyncSession, video_id: str, version_number: int = 1) -> bool:
        """Run full AI pipeline: Content analysis, 5 title candidates, description, tags, thumbnail concepts."""
        video_q = await db.execute(
            select(Video).where(Video.id == video_id)
        )
        video = video_q.scalar_one_or_none()
        if not video:
            return False

        file_info_q = await db.execute(
            select(VideoFile).where(VideoFile.video_id == video_id)
        )
        file_info = file_info_q.scalar_one_or_none()

        provider = ai_factory.get_provider()

        # 1. Content Analysis
        content_text = f"Title: {video.title}. Video length: {file_info.duration_seconds if file_info else 0} seconds."
        analysis_res = await provider.analyze_content(content_text)

        analysis = VideoAnalysis(
            video_id=video.id,
            summary=analysis_res.summary,
            topics=analysis_res.topics,
            keywords=analysis_res.keywords,
            entities=analysis_res.entities,
            target_audience=analysis_res.target_audience,
            content_category=analysis_res.content_category,
            important_moments=analysis_res.important_moments
        )
        db.add(analysis)

        # 2. Metadata Generation (versioned)
        meta_gen = MetadataGeneration(
            video_id=video.id,
            version_number=version_number,
            ai_provider=settings.DEFAULT_AI_PROVIDER,
            model_name="default",
            prompt_preset=settings.DEFAULT_AI_QUALITY_PRESET,
            is_active=True
        )
        db.add(meta_gen)
        await db.flush()

        # 3. 5 Title Candidates
        titles_res = await provider.generate_titles(analysis_res.summary, analysis_res.topics, count=5)
        for i, tc in enumerate(titles_res.titles):
            title_text = tc.get("title", f"Title Candidate {i+1}")
            title_cand = TitleCandidate(
                metadata_generation_id=meta_gen.id,
                title_text=title_text,
                reasoning=tc.get("reasoning", ""),
                estimated_intent=tc.get("intent", "Discovery"),
                character_length=len(title_text),
                candidate_index=i + 1,
                is_selected=(i == 0)  # Pre-select candidate 1 by default
            )
            db.add(title_cand)

        # 4. Description
        desc_res = await provider.generate_description(analysis_res.summary, content_text)
        desc_record = DescriptionRecord(
            metadata_generation_id=meta_gen.id,
            short_description=desc_res.short_description,
            long_description=desc_res.long_description,
            call_to_action=desc_res.call_to_action,
            links_placeholder=desc_res.links_placeholder,
            hashtags=desc_res.hashtags,
            chapters=desc_res.chapters
        )
        db.add(desc_record)

        # 5. Tags
        tags_res = await provider.generate_tags(analysis_res.summary, analysis_res.topics)
        tag_record = TagRecord(
            metadata_generation_id=meta_gen.id,
            primary_keywords=tags_res.primary_keywords,
            secondary_keywords=tags_res.secondary_keywords,
            long_tail_keywords=tags_res.long_tail_keywords,
            combined_tags_string=tags_res.combined_tags_string,
            tag_count=len(tags_res.primary_keywords + tags_res.secondary_keywords + tags_res.long_tail_keywords)
        )
        db.add(tag_record)

        # 6. Thumbnail Concepts
        first_title = titles_res.titles[0].get("title", video.title) if titles_res.titles else video.title
        thumb_res = await provider.generate_thumbnail_concepts(analysis_res.summary, first_title)
        for i, concept in enumerate(thumb_res.concepts):
            thumb = ThumbnailRecord(
                video_id=video.id,
                metadata_generation_id=meta_gen.id,
                concept_title=concept.get("concept_title", f"Concept {i+1}"),
                text_suggestions=concept.get("text_suggestions", ""),
                visual_composition=concept.get("visual_composition", ""),
                subject_placement=concept.get("subject_placement", ""),
                background_concept=concept.get("background_concept", ""),
                is_selected=(i == 0),
                status="DRAFT"
            )
            db.add(thumb)

        # Transition status to READY_FOR_APPROVAL
        video.status = "READY_FOR_APPROVAL"
        video.quality_status = "READY"

        notification = Notification(
            title="AI Analysis Complete — Approval Required",
            message=f"Metadata and thumbnail concepts generated for '{video.title}'. Awaiting creator review.",
            notification_type="APPROVAL_REQUIRED",
            severity="WARNING",
            deep_link=f"/videos/{video.id}"
        )
        db.add(notification)

        await db.commit()
        system_logger.info(f"AI pipeline completed for video '{video.title}'")
        return True

    @staticmethod
    async def get_video_detail(db: AsyncSession, video_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve complete video record with relationships for the detail/review page."""
        q = await db.execute(
            select(Video)
            .options(
                selectinload(Video.file_info),
                selectinload(Video.analysis),
                selectinload(Video.metadata_generations).selectinload(MetadataGeneration.titles),
                selectinload(Video.metadata_generations).selectinload(MetadataGeneration.description),
                selectinload(Video.metadata_generations).selectinload(MetadataGeneration.tags),
                selectinload(Video.thumbnails)
            )
            .where(Video.id == video_id)
        )
        video = q.scalar_one_or_none()
        if not video:
            return None

        # Determine active metadata generation
        active_meta = None
        if video.metadata_generations:
            active_meta = next((m for m in video.metadata_generations if m.is_active), video.metadata_generations[-1])

        titles = active_meta.titles if active_meta else []
        description = active_meta.description if active_meta else None
        tags = active_meta.tags if active_meta else None
        selected_title = next((t for t in titles if t.is_selected), titles[0] if titles else None)
        selected_thumb = next((th for th in video.thumbnails if th.is_selected), video.thumbnails[0] if video.thumbnails else None)

        qc = quality_checker.evaluate(
            video=video,
            file_info=video.file_info,
            selected_title=selected_title,
            description=description,
            tags=tags,
            selected_thumbnail=selected_thumb,
            channel_connected=False  # Checked against channel in route
        )

        return {
            "video": video,
            "file_info": video.file_info,
            "titles": titles,
            "description": description,
            "tags": tags,
            "thumbnails": video.thumbnails,
            "quality_check": qc,
            "summary": video.analysis.summary if video.analysis else ""
        }


video_service = VideoService()
