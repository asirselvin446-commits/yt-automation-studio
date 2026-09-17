"""
Frame Extractor — Extracts thumbnail candidate frames from video files
using FFmpeg. Captures frames at key intervals for AI-based thumbnail
concept selection.
"""
import os
import subprocess
import json
from pathlib import Path
from typing import List, Optional
from app.core.config import settings
from app.core.logging import agent_logger


class FrameExtractor:
    """Extract thumbnail candidate frames from video files using FFmpeg."""

    FFMPEG_CMD = "ffmpeg"

    def extract_thumbnail_candidates(
        self,
        video_path: str,
        output_dir: Optional[str] = None,
        num_frames: int = 6,
        video_id: Optional[str] = None,
    ) -> List[str]:
        """
        Extract evenly-spaced frames from a video for thumbnail candidates.

        Args:
            video_path: Path to the source video file.
            output_dir: Directory to save extracted frames. Defaults to THUMBNAILS/<video_id>.
            num_frames: Number of frames to extract (default 6).
            video_id: Optional video identifier for organizing outputs.

        Returns:
            List of paths to extracted frame images.
        """
        path = Path(video_path)
        if not path.exists():
            agent_logger.error(f"Video file not found: {video_path}")
            return []

        # Determine output directory
        if output_dir is None:
            vid_id = video_id or path.stem
            output_dir = str(settings.thumbnails_path / vid_id)
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Get video duration
        duration = self._get_duration(video_path)
        if duration <= 0:
            agent_logger.error(f"Could not determine video duration: {video_path}")
            return []

        # Skip first and last 5% of the video (usually intros/outros)
        start_offset = duration * 0.05
        end_offset = duration * 0.95
        usable_duration = end_offset - start_offset

        if usable_duration <= 0:
            start_offset = 0
            usable_duration = duration

        # Calculate timestamps for evenly-spaced frames
        interval = usable_duration / (num_frames + 1)
        timestamps = [start_offset + interval * (i + 1) for i in range(num_frames)]

        extracted_paths = []
        for i, ts in enumerate(timestamps):
            output_file = os.path.join(output_dir, f"thumb_candidate_{i + 1:02d}.jpg")
            success = self._extract_frame_at(video_path, ts, output_file)
            if success:
                extracted_paths.append(output_file)

        agent_logger.info(
            f"Extracted {len(extracted_paths)}/{num_frames} thumbnail candidates from {path.name}"
        )
        return extracted_paths

    def extract_frame_at_timestamp(
        self, video_path: str, timestamp: float, output_path: str
    ) -> bool:
        """Extract a single frame at a specific timestamp."""
        return self._extract_frame_at(video_path, timestamp, output_path)

    def extract_keyframes(
        self, video_path: str, output_dir: str, max_frames: int = 10
    ) -> List[str]:
        """
        Extract keyframes (I-frames) from the video. These often represent
        scene changes and make good thumbnail candidates.
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        output_pattern = os.path.join(output_dir, "keyframe_%03d.jpg")

        cmd = [
            self.FFMPEG_CMD,
            "-i", video_path,
            "-vf", f"select='eq(pict_type\\,I)',scale=1920:-1",
            "-vsync", "vfr",
            "-frames:v", str(max_frames),
            "-q:v", "2",
            output_pattern,
            "-y",
            "-loglevel", "error",
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120
            )
            if result.returncode != 0:
                agent_logger.error(f"Keyframe extraction failed: {result.stderr}")
                return []

            # Collect output files
            extracted = sorted(
                str(f) for f in Path(output_dir).glob("keyframe_*.jpg") if f.is_file()
            )
            agent_logger.info(f"Extracted {len(extracted)} keyframes from {Path(video_path).name}")
            return extracted[:max_frames]

        except subprocess.TimeoutExpired:
            agent_logger.error(f"Keyframe extraction timed out: {video_path}")
            return []
        except FileNotFoundError:
            agent_logger.error("FFmpeg not found. Ensure FFmpeg is in PATH.")
            return []

    def _extract_frame_at(self, video_path: str, timestamp: float, output_path: str) -> bool:
        """Extract a single high-quality frame at the given timestamp."""
        cmd = [
            self.FFMPEG_CMD,
            "-ss", f"{timestamp:.2f}",
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "2",
            "-vf", "scale=1920:-1",
            output_path,
            "-y",
            "-loglevel", "error",
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and Path(output_path).exists():
                return True
            else:
                agent_logger.debug(f"Frame extraction failed at {timestamp:.2f}s: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            agent_logger.error(f"Frame extraction timed out at {timestamp:.2f}s")
            return False
        except FileNotFoundError:
            agent_logger.error("FFmpeg not found. Ensure FFmpeg is in PATH.")
            return False

    def _get_duration(self, video_path: str) -> float:
        """Get video duration in seconds using FFprobe."""
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            video_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return float(data.get("format", {}).get("duration", 0))
        except Exception as e:
            agent_logger.error(f"Duration probe failed for {video_path}: {e}")
        return 0.0


# Singleton
frame_extractor = FrameExtractor()
