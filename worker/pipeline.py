"""Process one queued video end to end (runs in GitHub Actions).

download from Supabase Storage → transcribe → AI metadata → YouTube upload →
delete the storage object → mark UPLOADED. Every step writes progress back to
Supabase so state is always recoverable, and the raw video is removed from
Supabase the moment YouTube has it.
"""
import os
import shutil

from config import config
from store import store
import storage
import transcribe as transcriber
import ai
import youtube


def process_item(item: dict) -> None:
    item_id = item["id"]
    work_path = os.path.join(config.WORK_DIR, f"{item_id}_{item['file_name']}")
    store.update_item(item_id, status="PROCESSING", attempts=item.get("attempts", 0) + 1)

    try:
        # 1. Fetch the bytes from Supabase Storage.
        print(f"[{item_id}] downloading {item['file_name']} from storage ...", flush=True)
        storage.download(item["storage_path"], work_path)

        # 2. Transcribe (Gemini multimodal).
        print(f"[{item_id}] transcribing ...", flush=True)
        transcript = transcriber.transcribe(
            work_path, item.get("mime_type") or "video/mp4", item["file_name"]
        )
        store.update_item(item_id, transcript=transcript)

        # 3. Generate title / description / tags.
        print(f"[{item_id}] generating metadata ...", flush=True)
        fallback = os.path.splitext(item["file_name"])[0]
        meta = ai.generate_metadata(transcript, fallback_title=fallback)
        store.update_item(item_id, ai_metadata=meta)

        # 4. Upload to YouTube.
        print(f"[{item_id}] uploading to YouTube ...", flush=True)
        result = youtube.upload_video(
            work_path,
            title=meta["title"], description=meta["description"], tags=meta["tags"],
            privacy_status=config.UPLOAD_PRIVACY_STATUS, category_id=config.UPLOAD_CATEGORY_ID,
        )

        # 5. YouTube has it — delete the raw video from Supabase Storage.
        storage.remove(item["storage_path"])

        store.update_item(
            item_id,
            status="UPLOADED",
            youtube_video_id=result["video_id"],
            youtube_url=result["url"],
            storage_deleted=True,
            error=None,
        )
        print(f"[{item_id}] DONE -> {result['url']} (storage cleaned)", flush=True)

    except Exception as e:  # noqa: BLE001 - record failures, don't crash the run
        attempts = item.get("attempts", 0) + 1
        status = "QUEUED" if attempts < config.MAX_ATTEMPTS else "FAILED"
        store.update_item(item_id, status=status, error=str(e)[:2000])
        print(f"[{item_id}] error (attempt {attempts} -> {status}): {e}", flush=True)
    finally:
        try:
            if os.path.exists(work_path):
                os.remove(work_path)
        except OSError:
            pass
        shutil.rmtree(config.WORK_DIR, ignore_errors=True)
