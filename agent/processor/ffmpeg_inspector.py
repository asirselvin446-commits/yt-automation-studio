import json
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path


class FFmpegInspector:
    @staticmethod
    def inspect(file_path: str) -> Dict[str, Any]:
        """Run ffprobe on target file and extract detailed container, video, and audio streams."""
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]

        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            probe_data = json.loads(res.stdout)
        except Exception as e:
            return {
                "error": str(e),
                "is_corrupted": True,
                "duration": 0.0,
                "has_audio": False
            }

        streams = probe_data.get("streams", [])
        fmt = probe_data.get("format", {})

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        duration = float(fmt.get("duration", 0.0))
        file_size = int(fmt.get("size", 0))

        # Video stream attributes
        width = None
        height = None
        fps = None
        video_codec = None
        video_bitrate = None

        if video_stream:
            width = video_stream.get("width")
            height = video_stream.get("height")
            video_codec = video_stream.get("codec_name")
            # Calculate FPS from r_frame_rate
            r_fps = video_stream.get("r_frame_rate", "30/1")
            try:
                num, den = map(int, r_fps.split("/"))
                fps = round(num / den, 2) if den != 0 else 30.0
            except Exception:
                fps = 30.0
            video_bitrate = int(video_stream.get("bit_rate", 0)) if video_stream.get("bit_rate") else None

        # Audio stream attributes
        has_audio = audio_stream is not None
        audio_codec = audio_stream.get("codec_name") if audio_stream else None
        audio_channels = int(audio_stream.get("channels", 0)) if audio_stream else None
        audio_sample_rate = int(audio_stream.get("sample_rate", 0)) if audio_stream else None

        return {
            "duration": duration,
            "file_size": file_size,
            "width": width,
            "height": height,
            "aspect_ratio": f"{width}:{height}" if width and height else None,
            "fps": fps,
            "video_codec": video_codec,
            "video_bitrate": video_bitrate,
            "has_audio": has_audio,
            "audio_codec": audio_codec,
            "audio_channels": audio_channels,
            "audio_sample_rate": audio_sample_rate,
            "container_format": fmt.get("format_name"),
            "is_corrupted": False,
            "raw": probe_data
        }


ffmpeg_inspector = FFmpegInspector()
