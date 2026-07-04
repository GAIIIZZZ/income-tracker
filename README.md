# Income Tracker — Bank Slip OCR → Local AI → Web Dashboard

Drag and drop (or drop into a folder) screenshots of bank transfer slips. The app OCRs
them (Thai + English), sends the text to a **local** LLM running in Ollama
(`qwen2.5:1.5b` by default — nothing leaves your computer) to pull out the sender's
name, date, time, and amount, stores everything in a local SQLite database, and gives
you a dashboard to review, correct, sort, save into named batches, and chart income
over time. It also supports "zone profiles" — calibrating exact crop regions per bank
app layout for more accurate extraction.

**Everything runs 100% locally.** No data ever leaves your machine except the OCR'd
text going to your own local Ollama instance on `localhost`.

---

## ⚠️ IMPORTANT — read before doing anything else

You **must** have these three things installed, or the app will not work at all:

| Requirement | Why | Get it |
|---|---|---|
| **Python 3.10+** | Runs the backend (FastAPI + OCR + AI pipeline) | https://www.python.org/downloads/ — ⚠️ during install, **check the box "Add python.exe to PATH"** |
| **Node.js (LTS)** | Runs the frontend web server | https://nodejs.org/ |
| **Ollama** | Runs the local AI model — the app cannot extract any data without this running | https://ollama.com |

After installing Ollama, you **must** also pull the model it uses. Open any terminal
and run:

```
ollama pull qwen2.5:1.5b
```

This is a ~1 GB download. **The app will silently fail to extract any data (or hang)
if Ollama isn't running or this model hasn't been pulled** — if things aren't working,
this is the first thing to check.

The first time you install the Python dependencies, it also downloads **PyTorch and
EasyOCR's recognition models (~1-2 GB total)**. This only happens once, but it needs a
working internet connection and can take several minutes — this is normal, not stuck.

---

## Option 1: Quick Start (recommended — double-click, no typing)

This project includes ready-made scripts so you never have to open a terminal or type
a command manually.

**Step 1.** Make sure the three prerequisites above are installed (Python, Node.js,
Ollama + the model pulled).

**Step 2.** Double-click **`setup.bat`** in the project's root folder.
This installs everything the app needs. It only needs to be run once (or again later
if you pull new code changes that add new dependencies). A black window will open and
show progress — wait for it to say `Setup complete!` before closing it.

**Step 3.** Double-click **`start_all.bat`**.
This opens two windows (backend + frontend) and automatically opens your browser to
the app at `http://localhost:3000`. Leave both windows open while you use the app —
closing either one stops that part of the app.

That's it — if Ollama is running with the model pulled, you're done. To stop the app,
close the two windows (or press Ctrl+C in each and press a key to close).

**Optional:** if you want images dropped directly into the `OCR\inbox` folder (instead
of only using the website's drag-and-drop) to be picked up automatically, also
double-click **`start_watcher.bat`**. This is optional — the website upload works
without it.

---

## Option 2: Manual Setup (step-by-step, using a terminal)

Use this if you prefer to see exactly what's happening, the `.bat` scripts don't work
on your machine, or you're on a different OS. All commands below are typed into a
terminal — on Windows this can be **PowerShell**, **Command Prompt**, or **Git Bash**.
Each numbered step says which folder to be in.

### 1. Set up the backend

Open a terminal **in the project's root folder**, then:

```
cd backend
python -m venv .venv
```

Activate the virtual environment — the command differs by shell:

```
.venv\Scripts\activate          (Command Prompt)
.venv\Scripts\Activate.ps1      (PowerShell)
source .venv/Scripts/activate   (Git Bash)
```

You should see `(.venv)` appear at the start of your terminal prompt. Then, still in
the `backend` folder:

```
pip install -r requirements.txt
```

⚠️ This downloads PyTorch + EasyOCR (~1-2 GB) the first time — it can take several
minutes. Do not close the terminal while it's running.

### 2. Start the backend

Still in the `backend` folder, with the virtual environment active:

```
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Leave this terminal open. You should see `Application startup complete.` and
`Uvicorn running on http://127.0.0.1:8000`. Check it worked by opening
`http://localhost:8000/api/health` in a browser — it should show `{"status":"ok"}`.

### 3. Set up and start the frontend

Open a **second, separate terminal window**, in the project's root folder:

```
cd frontend
npm install
node server.js
```

Leave this terminal open too. It should print `Frontend running at
http://localhost:3000`.

### 4. Open the app

Go to `http://localhost:3000` in your browser. Both terminal windows (backend and
frontend) need to stay open while you use the app.

### 5. (Optional) Folder watcher

If you want to drop images directly into `OCR/inbox` and have them picked up
automatically (instead of only using the website's upload area), open a **third**
terminal, in the project root:

```
cd backend
.venv\Scripts\activate
python -m app.watcher
```

---

## How to use the app once it's running

1. **Upload slips** — drag and drop images (or a whole folder of them) onto the upload
   area, or click it to choose files. Each one gets OCR'd and AI-structured
   automatically; this can take 10-30 seconds per image on CPU.
2. **Review the table** — check the extracted Name / Date / Time / Amount / Notes.
   Click the pencil icon on a row to edit any field, then confirm or cancel.
3. **Working sets** — everything you upload lands in "Current (unsaved)" first. Click
   "Add more Set +" in the sidebar if you want a second, independent batch of uploads
   going at the same time (e.g. two different folders).
4. **Save or Clear** — once a batch of transactions looks right, click **Save
   Transactions** to lock it in as a named, permanent record (this also re-runs the AI
   once more as a double-check and flags anything it disagrees with). Click **Clear
   shown** to throw away the current unsaved batch and start over.
5. **Saved batches** (left sidebar) — rename, delete, star as favorite, or sort them.
   Click one to view its transactions read-only-ish (still editable) alongside its
   saved/last-edited timestamps.
6. **Gallery tab** — a visual grid of every processed slip's image + extracted details.
7. **Zones tab** — for better accuracy, calibrate a "zone profile" per bank app: upload
   one sample slip, draw a box around each field (name/date/time/amount), and save.
   Future uploads are matched to it by visual similarity to the sample — no need to
   know or type which bank it is. Export/Import lets you back up or share your
   calibrations as one file; "Save as Default" makes them auto-load for anyone who
   installs this project fresh.
8. **Graph** — income over time at the bottom of the Transactions tab, filterable by
   date range and by status (correct / pending / needs review), with a checkbox legend.

---

## Troubleshooting / Common Errors

| Symptom | Likely cause / fix |
|---|---|
| Uploads sit at "pending" forever, or every slip lands in "needs review" with no data extracted | **Ollama isn't running**, or you haven't run `ollama pull qwen2.5:1.5b`. Open a terminal and run `ollama list` to check the model is there; run `ollama serve` if Ollama itself isn't running. |
| `pip install -r requirements.txt` fails or is extremely slow | Usually a slow/unstable internet connection (PyTorch is a large download). Just retry — pip resumes what it can. Make sure you're using Python 3.10+ (`python --version`). |
| `'python' is not recognized` / `'node' is not recognized` | The prerequisite isn't installed, or wasn't added to your system PATH. Reinstall and make sure to check "Add to PATH" during setup, then **open a new terminal window** (PATH changes don't apply to already-open terminals). |
| Backend crashes on startup with a Unicode/encoding error on Windows | Make sure `PYTHONIOENCODING=utf-8` is set before starting uvicorn — `start_backend.bat` already does this for you; if running manually, set it yourself: `set PYTHONIOENCODING=utf-8` (Command Prompt) or `$env:PYTHONIOENCODING="utf-8"` (PowerShell) before the `uvicorn` command. |
| Browser shows nothing / connection refused at `localhost:3000` | The frontend server isn't running, or the backend isn't running (the frontend depends on the backend being up first). Check both terminal windows for errors. |
| Port already in use (`8000` or `3000`) | Another instance of the app (or something else) is already using that port. Close any other running copy of this app first. |
| Dates/times look wrong on a specific bank's slips | The small local AI model can misread OCR text (Thai months, 12-hour times, etc.) — edit the value directly in the table; it's always correctable. If it's consistently wrong for one bank, calibrating a Zone Profile for that bank (see the Zones tab) usually helps a lot. |

---

## Project structure

```
setup.bat              first-time install (Option 1)
start_all.bat           launches backend + frontend + opens the browser (Option 1)
start_backend.bat       launches just the backend
start_frontend.bat      launches just the frontend
start_watcher.bat       optional: auto-processes files dropped into OCR/inbox

backend/                FastAPI app, SQLite database, OCR + AI pipeline
  app/pipeline/          OCR (EasyOCR), LLM (Ollama), zone matching/cropping
  app/routes/            REST API endpoints
  data/                  the SQLite database lives here (not committed to git)

frontend/               Express static server + vanilla JS/HTML/CSS dashboard

OCR/                    working folders for images (not committed to git)
  inbox/                 drop images here for the optional folder watcher
  uploads/                staging area for website uploads
  processed/              successfully-processed images, organized by month
  needs_review/           images that failed OCR/AI extraction
  zone_samples/           calibration sample images for Zone Profiles
```

## Configuration

Environment variables (backend), all optional:

- `OLLAMA_HOST` — default `http://localhost:11434`
- `OLLAMA_MODEL` — default `qwen2.5:1.5b` (swap in another pulled model to compare
  accuracy — no code changes needed)

## Data & privacy

The SQLite database (`backend/data/app.db`), all slip images (`OCR/`), and any zone
profile seed file are **excluded from git** (see `.gitignore`) because they contain
real names, amounts, and partial account numbers. Only the application code is meant
to be shared/committed — never commit your own `backend/data/` folder or real slip
images to a public place.
