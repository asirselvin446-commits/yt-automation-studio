# YT Automation — Auto Uploader (no server, laptop can be off)

Drop a video in a folder on your laptop. While the laptop is on, it's pushed to
Supabase. **GitHub Actions** then transcribes it, writes the title/description/
tags, and uploads it to YouTube — even after your laptop is off. Supabase only
holds the video briefly; it's deleted from both Supabase and your folder once the
upload succeeds.

```
Laptop ON   ── push_local.py ─►  Supabase Storage (video)  +  ingest_items row (QUEUED)
                                        │  (pings GitHub)
Laptop OFF  ── GitHub Actions ─►  download → transcribe (Gemini) → title/desc/tags (Gemini)
                                  → upload to YouTube → DELETE video from Supabase → UPLOADED
Laptop ON   ── push_local.py ─►  deletes the local file for anything already UPLOADED
```

Nothing is uploaded twice: every video's SHA-256 is recorded, so re-scanning the
folder or re-running the workflow does nothing for videos already handled.

---

## One-time setup

1. **Supabase tables** — run [`db/schema.sql`](db/schema.sql) in Supabase → SQL Editor.
2. **Gemini key** — create at <https://aistudio.google.com/apikey>.
3. **Enable YouTube Data API v3** in Google Cloud Console.
4. **⚠️ Publish the OAuth consent screen to "Production"** (Google Cloud → OAuth
   consent screen). In *Testing* mode refresh tokens **expire after 7 days** and
   the uploader would stop weekly; in *Production* the token is long-lived.
5. **Fill `worker/.env`** — copy `.env.example`, set every value. Generate
   `WORKER_SECRET_KEY` with `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
6. **Authorize YouTube once** (locally):
   ```bash
   cd worker && pip install -r requirements.txt && python authorize.py
   ```
   Grant access; the encrypted token is saved to Supabase.
7. **GitHub** — push this repo, then in **Settings → Secrets and variables →
   Actions** add the same values as secrets: `SUPABASE_URL`,
   `SUPABASE_SERVICE_ROLE_KEY`, `STORAGE_BUCKET`, `GOOGLE_CLIENT_ID`,
   `GOOGLE_CLIENT_SECRET`, `GEMINI_API_KEY`, `WORKER_SECRET_KEY`, and optionally
   `GEMINI_MODEL`, `UPLOAD_PRIVACY_STATUS`, `UPLOAD_CATEGORY_ID`.
   The workflow [`.github/workflows/upload.yml`](../.github/workflows/upload.yml)
   runs every 6 hours, on the "Run workflow" button, and whenever `push_local.py`
   pings it.

### Instant uploads (optional)
To make the upload start the moment you add a video (instead of waiting for the
6-hour cron), create a fine-grained GitHub PAT with **Contents: read/write** on
the repo and set `GITHUB_TOKEN` + `GITHUB_REPO` in `worker/.env`.

---

## Daily use
```bash
cd worker
python push_local.py            # push new videos + clean up finished ones
python push_local.py --loop     # or keep it running while you work
```
Put a video in your `LOCAL_WATCH_FOLDER` → it uploads to Supabase and queues.
GitHub Actions does the rest. Change `UPLOAD_PRIVACY_STATUS` to `public` /
`unlisted` if you don't want `private`.

> Tip: schedule `python worker/push_local.py` in **Windows Task Scheduler** (e.g.
> at logon / every 15 min) so pushing + local cleanup happen automatically.

## Test the uploader locally (before trusting the cloud)
With `.env` filled and `authorize.py` done, you can run the GitHub-side step on
your own machine:
```bash
cd worker && python main.py     # drains the queue once, same as the Action
```

## Notes & limits
- **Storage stays tiny:** each video is deleted from Supabase right after YouTube
  gets it, so the free 1 GB tier is fine as long as you don't queue many huge
  videos at once.
- **Gemini limits:** free tier has request caps and a ~2 GB/video Files API
  limit; enable billing on the key for heavy use.
- **Security:** the YouTube refresh token is Fernet-encrypted at rest in Supabase;
  the Supabase bucket is private (service-key access only).
