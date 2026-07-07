# Income Tracker — Cloud Alternative (Streamlit + Supabase + Groq)

A second, optional way to run this project: a shareable web link instead of a local-only app.
This is a genuine alternative build, kept separate from the local app in the project root —
it doesn't replace it.

**What's different from the local app, and why:**

| | Local app (project root) | Cloud alt (this folder) |
|---|---|---|
| Frontend | Custom Express + HTML/JS dashboard | Streamlit |
| Database | SQLite (`backend/data/app.db`) | Supabase (Postgres, free tier) |
| Image storage | Local `OCR/` folders | Supabase Storage (free tier) |
| OCR | EasyOCR, local | EasyOCR, local (same — still runs on whatever server hosts this) |
| AI structuring | Ollama, local, 100% private | Groq API (free tier) — text leaves your server to Groq |
| Zone Profile calibration | Yes | Not included (custom canvas UI, no simple Streamlit equivalent yet) |
| Cost | Free forever, no accounts needed | Free, but requires a Supabase account + a Groq API key |

Use this if you want a link you or friends can open in a browser with nothing installed
locally. Use the local app if you want everything 100% private with zero external accounts.

**Feature parity with the local app:**
- Gallery tab (visual grid of processed slips)
- Saved batches: rename, delete, favorite (⭐)
- Multiple concurrent "draft sets" (+ Add another set), matching the local app's working sets
- Status filtering (pending / needs review) on both the review table and the saved view
- Income graph filterable by date range and status
- Basic theming matching the local app's dark color palette (`.streamlit/config.toml`)

**Still not included:** Zone Profile calibration (the custom canvas-drawing tool for
calibrating exact crop regions per bank app) — no simple Streamlit equivalent for that yet.

> **If you deployed an earlier version of this app**, re-run the updated
> `supabase_schema.sql` in Supabase's SQL Editor before pulling the new code — it adds a
> `batches` table and a `draft_slot` column. It's written to be safe to re-run (uses
> `IF NOT EXISTS` / `DROP POLICY IF EXISTS`), so it won't touch your existing data.

---

## 1. Create a free Supabase project

1. Sign up at https://supabase.com (free tier, no credit card required for the free plan).
2. Create a new project. Wait for it to finish provisioning (~2 minutes).
3. Go to **SQL Editor**, paste the contents of `supabase_schema.sql` from this folder, and run it.
4. Go to **Storage** → **New bucket** → name it exactly `slip-images` → toggle **Public bucket** on.
5. Go to **Project Settings → API**. You'll need two values for later:
   - **Project URL** (`SUPABASE_URL`)
   - **`anon` `public` key** (`SUPABASE_KEY`) — NOT the `service_role` key.

## 2. Get a free Groq API key

1. Sign up at https://console.groq.com (free tier).
2. Go to **API Keys** → **Create API Key** → copy it (`GROQ_API_KEY`). Groq's free tier has
   rate limits (requests per minute/day) but no cost.

## 3a. Run it locally first (recommended, to test before deploying)

```
cd cloud
python -m venv .venv
.venv\Scripts\activate          (or .venv\Scripts\Activate.ps1 in PowerShell)
pip install -r requirements.txt
```

Copy the secrets template and fill in your real values:
```
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
```
Edit `.streamlit/secrets.toml` with the `SUPABASE_URL`, `SUPABASE_KEY`, and `GROQ_API_KEY`
from steps 1-2.

Run it:
```
streamlit run streamlit_app.py
```
It opens in your browser automatically (usually `http://localhost:8501`).

## 3b. Deploy it for free on Streamlit Community Cloud (the actual shareable link)

1. Push this repo to GitHub (already done, if you're reading this from the repo).
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **New app** → pick this repository → set:
   - **Branch**: your default branch
   - **Main file path**: `cloud/streamlit_app.py`
4. Before deploying, click **Advanced settings → Secrets** and paste:
   ```
   SUPABASE_URL = "..."
   SUPABASE_KEY = "..."
   GROQ_API_KEY = "..."
   ```
   (same three values from steps 1-2 — never commit these to the repo itself)
5. Click **Deploy**. First deploy takes a while (installing PyTorch/EasyOCR, ~1-2GB) — this
   is normal. Once done, you get a public `https://your-app-name.streamlit.app` link anyone
   can open directly, no local setup needed.

---

## Notes / limitations

- **Free tier limits**: Streamlit Community Cloud free apps have limited RAM/CPU and can go
  to sleep after inactivity (a visit wakes it back up after ~30-60 seconds). Supabase's free
  tier pauses a project after a week of no activity (visiting the app resumes it). Groq's free
  tier has per-minute/day rate limits — heavy simultaneous use by several friends could hit them.
- **No login system**: anyone with the link can see and edit all data, per `supabase_schema.sql`'s
  policy. Fine for sharing with a small trusted group of friends; not meant for a public audience.
- **Not private**: OCR'd slip text is sent to Groq's API to be structured — unlike the local
  app, this is no longer 100% on-device.
