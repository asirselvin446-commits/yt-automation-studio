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
import autosource_assemble

IMAGE_STYLE = "cinematic, ultra detailed, dramatic lighting, photographic, no text, no watermark"


def _today_start_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def _generate_one(cfg: dict, publish_at: str | None) -> None:
    niche = (cfg.get("niche") or "amazing facts").strip()
    provider = (cfg.get("provider") or "edge").strip()
    voice = (cfg.get("voice") or "").strip()
    fish_key = (cfg.get("fish_api_key") or "").strip()
    fish_voice = (cfg.get("fish_voice") or "").strip()

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
            first_prompt = script["beats"][0]["image_prompt"] if script["beats"] else niche
            segments.append({"narration": script["hook"], "image_prompt": first_prompt})
        segments.extend(script["beats"])

        # 2. Voice + image per segment.
        beats = []
        for i, seg in enumerate(segments):
            store.update_autosource_run(run_id, stage=f"voicing {i + 1}/{len(segments)}")
            audio_path = os.path.join(workdir, f"aud{i}.mp3")
            autosource_voice.synthesize(
                seg["narration"], audio_path,
                provider=provider, voice=voice,
                fish_api_key=fish_key, fish_voice=fish_voice,
            )

            store.update_autosource_run(run_id, stage=f"illustrating {i + 1}/{len(segments)}")
            image_path = os.path.join(workdir, f"img{i}.jpg")
            autosource_visuals.fetch_image(
                seg["image_prompt"], image_path, seed=(hash(run_id) + i) % 100000,
                style=IMAGE_STYLE,
            )
            beats.append({"image_path": image_path, "audio_path": audio_path,
                          "text": seg["narration"]})

        # 3. Assemble.
        store.update_autosource_run(run_id, stage="assembling video")
        final_path = os.path.join(workdir, "final.mp4")
        autosource_assemble.build_video(beats, final_path, workdir)

        # 4. Upload to YouTube.
        stage = "scheduling upload" if publish_at else "uploading to youtube"
        store.update_autosource_run(run_id, stage=stage)
        result = youtube.upload_video(
            final_path,
            title=script["title"],
            description=script["description"],
            tags=script["tags"],
            privacy_status="public",
            category_id=config.UPLOAD_CATEGORY_ID,
            publish_at=publish_at,
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
