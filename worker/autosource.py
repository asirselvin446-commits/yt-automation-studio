"""Auto-source content engine — GitHub Actions entry point.

Runs entirely in the cloud (no laptop needed). Each run:

  1. reads the niche/voice/frequency config the desktop app saved to Supabase,
  2. writes an original script with Gemini,
  3. narrates it (edge-tts / Fish) and generates an image per line,
  4. assembles a captioned MP4 with ffmpeg,
  5. uploads it straight to YouTube (public, or drip-scheduled),
  6. records every stage back to Supabase so the app shows live status.

Two modes:
  * daily   (scheduled cron)      -> top up to `per_day` videos for today.
  * oneshot (AUTOSOURCE_ONESHOT)  -> make exactly one now (the app's "Generate now").
"""
import os
import shutil
from datetime import datetime, timedelta, timezone

from config import config
from store import store
import youtube
import autosource_ai
import autosource_voice
import autosource_visuals
import autosource_media
import autosource_assemble

IMAGE_STYLE = "cinematic, ultra detailed, dramatic lighting, photographic, no text, no watermark"

# Video dimensions per format.
_DIMS = {"shorts": (1080, 1920), "landscape": (1280, 720)}
# Keep Shorts comfortably under a minute.
_MAX_SECONDS = {"shorts": 55.0, "landscape": 180.0}


def _today_start_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def _generate_one(cfg: dict, publish_at: str | None) -> None:
    niche = (cfg.get("niche") or "amazing facts").strip()
    provider = (cfg.get("provider") or "edge").strip()
    voice = (cfg.get("voice") or "").strip()
    fish_key = (cfg.get("fish_api_key") or "").strip()
    fish_voice = (cfg.get("fish_voice") or "").strip()
    eleven_key = (cfg.get("eleven_api_key") or "").strip()
    eleven_voice = (cfg.get("eleven_voice") or "").strip()
    pexels_key = (cfg.get("pexels_api_key") or "").strip()
    fmt = (cfg.get("format") or "shorts").strip().lower()
    if fmt not in _DIMS:
        fmt = "shorts"
    width, height = _DIMS[fmt]
    max_seconds = _MAX_SECONDS[fmt]

    run_id = store.start_autosource_run(niche)
    workdir = os.path.join(config.WORK_DIR, f"autosource_{run_id}")
    os.makedirs(workdir, exist_ok=True)

    try:
        # 1. Script.
        store.update_autosource_run(run_id, stage="writing script")
        script = autosource_ai.generate_script(niche, store.recent_autosource_topics())
        store.update_autosource_run(
            run_id, topic=script["topic"], title=script["title"], stage="script ready",
        )

        # Assemble the ordered spoken segments (hook first, then beats).
        segments = []
        if script.get("hook"):
            first = script["beats"][0] if script["beats"] else {}
            segments.append({
                "narration": script["hook"],
                "image_prompt": first.get("image_prompt", niche),
                "visual_query": first.get("visual_query", niche),
            })
        segments.extend(script["beats"])

        # 2. Voice + visual per segment. Prefer real stock B-roll video; fall
        #    back to a generated AI image with motion. Stop once we hit the
        #    length cap so Shorts stay under a minute.
        beats = []
        total = 0.0
        for i, seg in enumerate(segments):
            store.update_autosource_run(run_id, stage=f"voicing {i + 1}/{len(segments)}")
            audio_path = os.path.join(workdir, f"aud{i}.mp3")
            autosource_voice.synthesize(
                seg["narration"], audio_path,
                provider=provider, voice=voice,
                fish_api_key=fish_key, fish_voice=fish_voice,
                eleven_api_key=eleven_key, eleven_voice=eleven_voice,
            )
            dur = autosource_assemble.probe_duration(audio_path)
            if beats and total + dur > max_seconds:
                break  # keep it within the format's length budget
            total += dur

            store.update_autosource_run(run_id, stage=f"sourcing footage {i + 1}/{len(segments)}")
            beat = {"audio_path": audio_path, "text": seg["narration"]}
            clip_path = os.path.join(workdir, f"vid{i}.mp4")
            got = autosource_media.fetch_clip(seg.get("visual_query", niche), clip_path, pexels_key)
            if got:
                beat["video_path"] = got
            else:
                image_path = os.path.join(workdir, f"img{i}.jpg")
                autosource_visuals.fetch_image(
                    seg["image_prompt"], image_path,
                    width=width, height=height,
                    seed=(hash(run_id) + i) % 100000, style=IMAGE_STYLE,
                )
                beat["image_path"] = image_path
            beats.append(beat)

        # 3. Assemble.
        store.update_autosource_run(run_id, stage="assembling video")
        final_path = os.path.join(workdir, "final.mp4")
        autosource_assemble.build_video(beats, final_path, workdir, width=width, height=height)

        # 4. Upload to YouTube. For Shorts, make sure the #Shorts signal is
        #    present (vertical + <60s + #Shorts => classified as a Short).
        title = script["title"]
        description = script["description"]
        tags = script["tags"]
        if fmt == "shorts":
            if "#short" not in title.lower():
                title = f"{title[:88]} #Shorts"
            if "#short" not in description.lower():
                description = f"{description}\n\n#Shorts"
            if not any("short" in t.lower() for t in tags):
                tags = (tags + ["shorts", "youtube shorts"])[:50]

        stage = "scheduling upload" if publish_at else "uploading to youtube"
        store.update_autosource_run(run_id, stage=stage)
        result = youtube.upload_video(
            final_path,
            title=title,
            description=description,
            tags=tags,
            privacy_status="public",
            category_id=config.UPLOAD_CATEGORY_ID,
            publish_at=publish_at,
            account_id=(cfg.get("account_id") or None),
        )

        store.update_autosource_run(
            run_id, status="DONE", stage="done",
            youtube_video_id=result["video_id"], youtube_url=result["url"],
            publish_at=publish_at, error=None,
        )
        print(f"[autosource] DONE -> {result['url']}", flush=True)

    except Exception as e:  # noqa: BLE001
        store.update_autosource_run(run_id, status="FAILED", stage="failed", error=str(e)[:2000])
        print(f"[autosource] FAILED: {e}", flush=True)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main() -> None:
    # Reuse the uploader's required-secret check (Supabase + Google + Gemini).
    missing = config.missing_for_worker()
    if missing:
        print(f"[fatal] missing required env: {', '.join(missing)}", flush=True)
        raise SystemExit(1)

    cfg = store.get_autosource_config()
    if not cfg or not cfg.get("enabled"):
        print("[autosource] disabled in app settings — nothing to do.", flush=True)
        return

    per_day = max(1, min(8, int(cfg.get("per_day") or 1)))
    oneshot = os.environ.get("AUTOSOURCE_ONESHOT", "").strip() in ("1", "true", "yes")

    if oneshot:
        print("[autosource] one-shot generation requested.", flush=True)
        _generate_one(cfg, publish_at=None)
        return

    # Honor the user's chosen daily upload time (stored as UTC "HH:MM"): don't
    # generate before it. The first hourly cron at/after the time posts it.
    post_time = (cfg.get("post_time_utc") or "").strip()
    if post_time:
        try:
            th, tm = (int(x) for x in post_time.split(":"))
            now = datetime.now(timezone.utc)
            target = now.replace(hour=th, minute=tm, second=0, microsecond=0)
            if now < target:
                print(f"[autosource] before scheduled time {post_time} UTC; skipping this check.", flush=True)
                return
        except Exception:
            pass

    already = store.count_autosource_done_since(_today_start_iso())
    todo = per_day - already
    if todo <= 0:
        print(f"[autosource] today's quota met ({already}/{per_day}); nothing to do.", flush=True)
        return

    print(f"[autosource] producing {todo} video(s) today ({already}/{per_day} done).", flush=True)
    interval_h = 24.0 / per_day
    for i in range(todo):
        # First one goes public now; the rest are drip-scheduled across the day.
        if already == 0 and i == 0:
            publish_at = None
        else:
            slot = already + i
            when = datetime.now(timezone.utc) + timedelta(hours=interval_h * i + 0.25)
            publish_at = when.isoformat()
        _generate_one(cfg, publish_at=publish_at)

    print("[autosource] run complete.", flush=True)


if __name__ == "__main__":
    main()
