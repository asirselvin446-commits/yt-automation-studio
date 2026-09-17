"""GitHub Actions entry point — drain the queue once, then exit.

Each workflow run processes every QUEUED video (download from Supabase →
transcribe → metadata → upload to YouTube → delete from Supabase) and stops when
the queue is empty. The laptop is not involved; this runs on GitHub's servers.
"""
from config import config
from store import store
import pipeline


def main() -> None:
    missing = config.missing_for_worker()
    if missing:
        print(f"[fatal] missing required env: {', '.join(missing)}", flush=True)
        raise SystemExit(1)

    print("YT Automation uploader run started.", flush=True)
    processed = 0
    while True:
        item = store.next_queued()
        if not item:
            break
        pipeline.process_item(item)
        processed += 1

    print(f"Run complete. Processed {processed} item(s).", flush=True)


if __name__ == "__main__":
    main()
