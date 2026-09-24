"""Assemble narration + per-beat media into a finished MP4 with ffmpeg.

Each beat becomes a clip sized to its narration. The visual is either a real
stock video clip (scaled/cropped to fill the frame) or, as a fallback, an AI
image with a slow Ken-Burns zoom. The spoken sentence is burned in as a large,
bold caption. Clips are then concatenated. Supports vertical Shorts (1080x1920)
and landscape (1280x720). ffmpeg ships on GitHub's Ubuntu runners.
"""
import os
import shutil
import subprocess
import textwrap
from typing import Any, Dict, List

import httpx

FPS = 30

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def _run(cmd: List[str], cwd: str) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True)
    return proc.returncode, proc.stderr


def probe_duration(path: str) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True,
        ).stdout.strip()
        return max(0.5, float(out))
    except Exception:
        return 4.0


def _prepare_font(workdir: str) -> str | None:
    for cand in _FONT_CANDIDATES:
        if os.path.exists(cand):
            try:
                shutil.copy(cand, os.path.join(workdir, "font.ttf"))
                return "font.ttf"
            except Exception:
                return None
    return None


def _write_caption(workdir: str, idx: int, text: str, wrap: int) -> str:
    wrapped = "\n".join(textwrap.wrap(text.strip(), width=wrap)) or " "
    name = f"cap{idx}.txt"
    with open(os.path.join(workdir, name), "w", encoding="utf-8") as f:
        f.write(wrapped)
    return name


def _caption_filter(font: str, caption_file: str, width: int, height: int) -> str:
    fontsize = max(28, int(width * 0.058))
    borderw = max(2, int(width * 0.004))
    # Centered horizontally, sitting in the lower third — the Shorts sweet spot.
    y = f"h*0.70-text_h/2"
    return (
        f"drawtext=fontfile={font}:textfile={caption_file}:reload=0:"
        f"fontcolor=white:fontsize={fontsize}:borderw={borderw}:bordercolor=black:"
        f"box=1:boxcolor=black@0.45:boxborderw={int(fontsize*0.4)}:"
        f"line_spacing={int(fontsize*0.2)}:x=(w-text_w)/2:y={y}"
    )


def _cover_chain(width: int, height: int) -> str:
    return (f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,fps={FPS}")


def _kenburns_chain(width: int, height: int, frames: int) -> str:
    return (
        f"scale={width * 2}:{height * 2}:force_original_aspect_ratio=increase,"
        f"crop={width * 2}:{height * 2},"
        f"zoompan=z='min(zoom+0.0008,1.20)':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height}:fps={FPS}"
    )


def _build_clip(workdir: str, beat: Dict[str, Any], duration: float,
                caption_file: str | None, font: str | None, out_name: str,
                width: int, height: int) -> bool:
    is_video = bool(beat.get("video_path"))
    if is_video:
        src = os.path.relpath(beat["video_path"], workdir)
        chain = _cover_chain(width, height)
    else:
        src = os.path.relpath(beat["image_path"], workdir)
        chain = _kenburns_chain(width, height, int(duration * FPS) + FPS)

    if caption_file and font:
        chain += "," + _caption_filter(font, caption_file, width, height)

    cmd = ["ffmpeg", "-y"]
    if is_video:
        cmd += ["-stream_loop", "-1", "-i", src]      # loop short clips to fill
    else:
        cmd += ["-loop", "1", "-i", src]
    cmd += [
        "-i", os.path.relpath(beat["audio_path"], workdir),
        "-filter_complex", f"[0:v]{chain}[v]",
        "-map", "[v]", "-map", "1:a",
        "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-r", str(FPS), "-shortest",
        out_name,
    ]
    rc, err = _run(cmd, workdir)
    if rc != 0 and caption_file:
        print("[autosource-assemble] caption render failed, retrying without caption", flush=True)
        return _build_clip(workdir, beat, duration, None, None, out_name, width, height)
    if rc != 0:
        print(f"[autosource-assemble] clip build failed: {err[-600:]}", flush=True)
    return rc == 0


def _download_music(url: str, workdir: str) -> str | None:
    """Download a royalty-free music track to workdir. Returns path or None."""
    try:
        dst = os.path.join(workdir, "music_src.mp3")
        with httpx.stream("GET", url, timeout=60.0, follow_redirects=True) as r:
            if r.status_code != 200:
                return None
            with open(dst, "wb") as f:
                for chunk in r.iter_bytes(chunk_size=256 * 1024):
                    f.write(chunk)
        return dst if os.path.getsize(dst) > 4096 else None
    except Exception as e:  # noqa: BLE001
        print(f"[autosource-assemble] music download failed: {e}", flush=True)
        return None


def mix_music(video_in: str, out_path: str, workdir: str, music_url: str = "") -> str:
    """Mix a soft background-music bed under the narration and write out_path.

    Uses the given royalty-free track (looped) if a URL is supplied and downloads;
    otherwise generates an original ambient pad (zero copyright/Content-ID risk).
    Music sits low under the voice with gentle fade in/out. Falls back to the
    original video (no music) if the mix fails, so a run never breaks on music.
    """
    dur = probe_duration(video_in)
    fade_out_start = max(0.0, dur - 2.0)
    vin = os.path.relpath(video_in, workdir)
    out_abs = os.path.abspath(out_path)

    track = _download_music(music_url, workdir) if music_url else None

    if track:
        # Loop the supplied track to cover the video, keep it well under the voice.
        cmd = [
            "ffmpeg", "-y", "-i", vin, "-stream_loop", "-1", "-i", os.path.relpath(track, workdir),
            "-filter_complex",
            f"[1:a]volume=0.14,afade=t=in:st=0:d=1.5,afade=t=out:st={fade_out_start:.2f}:d=2[m];"
            f"[0:a][m]amix=inputs=2:duration=first:dropout_transition=0,dynaudnorm=f=250[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", out_abs,
        ]
    else:
        # Original generated ambient pad — a calm major chord with slow movement.
        pad = ("aevalsrc="
               "'0.6*sin(2*PI*130.81*t)+0.5*sin(2*PI*196.00*t)+0.4*sin(2*PI*261.63*t)'"
               f":s=44100:d={dur:.2f}")
        cmd = [
            "ffmpeg", "-y", "-i", vin, "-f", "lavfi", "-t", f"{dur:.2f}", "-i", pad,
            "-filter_complex",
            f"[1:a]lowpass=f=1300,tremolo=f=0.12:d=0.5,aecho=0.8:0.85:110:0.3,"
            f"volume=0.10,afade=t=in:st=0:d=2,afade=t=out:st={fade_out_start:.2f}:d=2[m];"
            f"[0:a][m]amix=inputs=2:duration=first:dropout_transition=0,dynaudnorm=f=250[a]",
            "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", out_abs,
        ]
    rc, err = _run(cmd, workdir)
    if rc != 0:
        print(f"[autosource-assemble] music mix failed ({err[-300:]}); using video without music", flush=True)
        shutil.copyfile(video_in, out_abs)
    return out_path


def build_video(beats: List[Dict[str, Any]], out_path: str, workdir: str,
                width: int = 1080, height: int = 1920,
                music: bool = True, music_url: str = "") -> str:
    """beats: [{audio_path, text, video_path? , image_path?}] -> out_path mp4."""
    os.makedirs(workdir, exist_ok=True)
    font = _prepare_font(workdir)
    wrap = 20 if height > width else 36  # tighter wrapping for vertical

    clip_names: List[str] = []
    for i, beat in enumerate(beats):
        dur = probe_duration(beat["audio_path"])
        cap = _write_caption(workdir, i, beat.get("text", ""), wrap)
        clip = f"clip{i}.mp4"
        if _build_clip(workdir, beat, dur, cap, font, clip, width, height):
            clip_names.append(clip)

    if not clip_names:
        raise RuntimeError("No clips could be assembled")

    with open(os.path.join(workdir, "concat.txt"), "w", encoding="utf-8") as f:
        for name in clip_names:
            f.write(f"file '{name}'\n")

    # Concatenate the clips (voiceover only) first.
    voiced = "voiced.mp4"
    rc, err = _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat.txt",
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-r", str(FPS),
        voiced,
    ], workdir)
    if rc != 0:
        raise RuntimeError(f"Concat failed: {err[-600:]}")

    voiced_abs = os.path.join(workdir, voiced)
    if music:
        return mix_music(voiced_abs, out_path, workdir, music_url)
    shutil.move(voiced_abs, os.path.abspath(out_path))
    return out_path
