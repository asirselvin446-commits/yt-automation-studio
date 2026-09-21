"""Assemble narration + generated images into a finished MP4 with ffmpeg.

Each beat becomes a clip: its image gets a slow Ken-Burns zoom for exactly the
length of its narration, with the spoken sentence burned in as a caption. The
clips are then concatenated into one video. ffmpeg ships on GitHub's Ubuntu
runners, so this all happens in the cloud.
"""
import os
import shutil
import subprocess
import textwrap
from typing import Any, Dict, List

FPS = 30
WIDTH = 1280
HEIGHT = 720

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
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
            dst = os.path.join(workdir, "font.ttf")
            try:
                shutil.copy(cand, dst)
                return "font.ttf"
            except Exception:
                return None
    return None


def _write_caption(workdir: str, idx: int, text: str) -> str:
    wrapped = "\n".join(textwrap.wrap(text.strip(), width=36)) or " "
    name = f"cap{idx}.txt"
    with open(os.path.join(workdir, name), "w", encoding="utf-8") as f:
        f.write(wrapped)
    return name


def _zoompan_chain() -> str:
    # Supersample x2 so the slow zoom stays crisp, then render at target size.
    return (
        f"scale={WIDTH * 2}:{HEIGHT * 2}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH * 2}:{HEIGHT * 2},"
        f"zoompan=z='min(zoom+0.0008,1.20)':d={{frames}}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={WIDTH}x{HEIGHT}:fps={FPS}"
    )


def _build_clip(workdir: str, img: str, aud: str, duration: float,
                caption_file: str | None, font: str | None, out_name: str) -> bool:
    frames = int(duration * FPS) + FPS  # a little headroom; -shortest trims it
    chain = _zoompan_chain().format(frames=frames)
    if caption_file and font:
        chain += (
            f",drawtext=fontfile={font}:textfile={caption_file}:reload=0:"
            f"fontcolor=white:fontsize=42:box=1:boxcolor=black@0.55:boxborderw=22:"
            f"line_spacing=10:x=(w-text_w)/2:y=h-text_h-70"
        )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", img,
        "-i", aud,
        "-filter_complex", f"[0:v]{chain}[v]",
        "-map", "[v]", "-map", "1:a",
        "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-r", str(FPS), "-shortest",
        out_name,
    ]
    rc, err = _run(cmd, workdir)
    if rc != 0 and caption_file:
        # Captioning can fail on runners without freetype fonts — retry clean.
        print(f"[autosource-assemble] caption render failed, retrying without caption", flush=True)
        return _build_clip(workdir, img, aud, duration, None, None, out_name)
    if rc != 0:
        print(f"[autosource-assemble] clip build failed: {err[-600:]}", flush=True)
    return rc == 0


def build_video(beats: List[Dict[str, Any]], out_path: str, workdir: str) -> str:
    """beats: [{image_path, audio_path, text}]. Writes final mp4 to out_path."""
    os.makedirs(workdir, exist_ok=True)
    font = _prepare_font(workdir)

    clip_names: List[str] = []
    for i, beat in enumerate(beats):
        img = os.path.relpath(beat["image_path"], workdir)
        aud = os.path.relpath(beat["audio_path"], workdir)
        dur = probe_duration(beat["audio_path"])
        cap = _write_caption(workdir, i, beat.get("text", ""))
        clip = f"clip{i}.mp4"
        if _build_clip(workdir, img, aud, dur, cap, font, clip):
            clip_names.append(clip)

    if not clip_names:
        raise RuntimeError("No clips could be assembled")

    concat_file = os.path.join(workdir, "concat.txt")
    with open(concat_file, "w", encoding="utf-8") as f:
        for name in clip_names:
            f.write(f"file '{name}'\n")

    rc, err = _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "concat.txt",
        "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-r", str(FPS),
        os.path.abspath(out_path),
    ], workdir)
    if rc != 0:
        raise RuntimeError(f"Concat failed: {err[-600:]}")
    return out_path
