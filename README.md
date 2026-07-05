**[English](#income-tracker--bank-slip-ocr--local-ai--web-dashboard) | [ภาษาไทย](#income-tracker--ระบบ-ocr-สลิปธนาคาร-ผ่าน-ai-ในเครื่อง--แดชบอร์ดเว็บ)**

---

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
| Browser shows nothing / connection refused at `localhost:3000` | Nothing is listening on port 3000 — the frontend server never started (or crashed). Go through this in order: **(1)** Look at the FRONTEND window — did it print an `[ERROR] Frontend dependencies not installed. Run setup.bat first.` message? If so, run `setup.bat` (or `cd frontend && npm install`). **(2)** Is the FRONTEND window still open at all? If you or something else closed it, the server stopped — just double-click `start_frontend.bat` again (or `start_all.bat`). **(3)** If the window is open but shows no `Frontend running at http://localhost:3000` line, run it manually to see the real error: `cd frontend` then `node server.js` — read whatever it prints. **(4)** Check the BACKEND window the same way — the frontend proxies API calls to it, and some pages won't behave until it's up; visit `http://localhost:8000/api/health` to confirm it says `{"status":"ok"}`. **(5)** If you still just get connection refused with no window open at all, something (antivirus, a previous crashed process) may be blocking it — see the port-in-use row below. |
| Port already in use (`8000` or `3000`) | Another instance of the app (or something else) is already using that port. On Windows, find and stop it: open Command Prompt and run `netstat -ano | findstr :3000` (or `:8000`) — the last column is the PID. Then run `taskkill /PID <that number> /F` to stop it, and start the app again. Most often this is just a previous copy of `start_all.bat` still running in the background — check for leftover BACKEND/FRONTEND windows first. |
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

---
---

# Income Tracker — ระบบ OCR สลิปธนาคาร ผ่าน AI ในเครื่อง → แดชบอร์ดเว็บ

ลากและวาง (หรือวางไว้ในโฟลเดอร์) ภาพหน้าจอสลิปโอนเงินธนาคาร แอปนี้จะทำการ OCR
(อ่านตัวอักษรจากภาพ) ทั้งภาษาไทยและอังกฤษ แล้วส่งข้อความไปยังโมเดล LLM ที่รันอยู่ **ในเครื่องของคุณเอง**
ผ่าน Ollama (ค่าเริ่มต้นคือ `qwen2.5:1.5b` — ข้อมูลจะไม่ถูกส่งออกจากเครื่องของคุณเลย) เพื่อดึงชื่อผู้โอน
วันที่ เวลา และจำนวนเงินออกมา จากนั้นเก็บทุกอย่างไว้ในฐานข้อมูล SQLite ในเครื่อง และมีแดชบอร์ดให้คุณ
ตรวจสอบ แก้ไข จัดเรียง บันทึกเป็นชุด (batch) ที่ตั้งชื่อได้ และดูกราฟรายรับตามช่วงเวลา นอกจากนี้ยังรองรับ
"Zone Profiles" — การกำหนดตำแหน่งพื้นที่ที่ต้องการครอปให้ตรงกับรูปแบบของแต่ละแอปธนาคาร
เพื่อให้การดึงข้อมูลแม่นยำขึ้น

**ทุกอย่างทำงาน 100% ในเครื่องของคุณ** ไม่มีข้อมูลใดออกจากเครื่องเลย ยกเว้นข้อความที่ OCR ได้
ซึ่งจะถูกส่งไปยัง Ollama ที่รันอยู่บน `localhost` ของคุณเองเท่านั้น

---

## ⚠️ สำคัญ — อ่านก่อนเริ่มทำอะไรทั้งสิ้น

คุณ **ต้อง** ติดตั้งสิ่งเหล่านี้ 3 อย่างก่อน ไม่เช่นนั้นแอปจะใช้งานไม่ได้เลย:

| สิ่งที่ต้องมี | ทำไมต้องมี | ไปโหลดที่ไหน |
|---|---|---|
| **Python 3.10 ขึ้นไป** | รันฝั่ง backend (FastAPI + OCR + AI pipeline) | https://www.python.org/downloads/ — ⚠️ ตอนติดตั้ง **ต้องติ๊กช่อง "Add python.exe to PATH"** |
| **Node.js (เวอร์ชัน LTS)** | รันเว็บเซิร์ฟเวอร์ฝั่ง frontend | https://nodejs.org/ |
| **Ollama** | รันโมเดล AI ในเครื่อง — แอปจะดึงข้อมูลไม่ได้เลยถ้าไม่มีตัวนี้ทำงานอยู่ | https://ollama.com |

หลังติดตั้ง Ollama แล้ว คุณ **ต้อง** ดึงโมเดลที่แอปใช้ด้วย เปิดเทอร์มินัลใดก็ได้แล้วรันคำสั่ง:

```
ollama pull qwen2.5:1.5b
```

ไฟล์นี้มีขนาดประมาณ 1 GB **ถ้า Ollama ไม่ได้ทำงานอยู่ หรือยังไม่ได้ดึงโมเดลนี้ แอปจะดึงข้อมูลไม่ได้เลย
(หรือค้าง) โดยไม่มีข้อความแจ้งเตือนที่ชัดเจน** — ถ้าแอปทำงานผิดปกติ ให้ตรวจสอบจุดนี้เป็นอันดับแรก

ตอนติดตั้ง Python dependencies ครั้งแรก ระบบจะดาวน์โหลด **PyTorch และโมเดลจดจำตัวอักษรของ
EasyOCR (รวมประมาณ 1-2 GB)** ด้วย ซึ่งจะเกิดขึ้นแค่ครั้งเดียว แต่ต้องใช้อินเทอร์เน็ตและอาจใช้เวลาหลายนาที
— เป็นเรื่องปกติ ไม่ใช่แอปค้าง

---

## Option 1: เริ่มต้นแบบง่าย (แนะนำ — แค่ดับเบิลคลิก ไม่ต้องพิมพ์คำสั่ง)

โปรเจกต์นี้มีสคริปต์สำเร็จรูปให้ใช้ เพื่อที่คุณจะได้ไม่ต้องเปิดเทอร์มินัลหรือพิมพ์คำสั่งเอง

**ขั้นตอนที่ 1.** ตรวจสอบว่าติดตั้งสิ่งที่จำเป็นทั้ง 3 อย่างข้างต้นแล้ว (Python, Node.js, Ollama
พร้อมดึงโมเดลแล้ว)

**ขั้นตอนที่ 2.** ดับเบิลคลิกไฟล์ **`setup.bat`** ในโฟลเดอร์หลักของโปรเจกต์
ไฟล์นี้จะติดตั้งทุกอย่างที่แอปต้องใช้ ต้องรันแค่ครั้งเดียว (หรือรันใหม่อีกครั้งถ้ามีการอัปเดตโค้ดที่เพิ่ม
dependency ใหม่) จะมีหน้าต่างสีดำเปิดขึ้นมาแสดงความคืบหน้า — รอจนกว่าจะขึ้นข้อความ `Setup complete!`
ก่อนปิดหน้าต่าง

**ขั้นตอนที่ 3.** ดับเบิลคลิกไฟล์ **`start_all.bat`**
ไฟล์นี้จะเปิดหน้าต่าง 2 หน้าต่าง (backend และ frontend) และเปิดเบราว์เซอร์ไปที่แอปที่
`http://localhost:3000` ให้อัตโนมัติ ให้เปิดทั้งสองหน้าต่างค้างไว้ระหว่างใช้งานแอป — ถ้าปิดหน้าต่างใด
หน้าต่างหนึ่ง ส่วนนั้นของแอปจะหยุดทำงาน

เท่านี้ก็เสร็จ — ถ้า Ollama ทำงานอยู่และดึงโมเดลแล้ว ก็ใช้งานได้เลย หากต้องการหยุดแอป ให้ปิดหน้าต่าง
ทั้งสอง (หรือกด Ctrl+C ในแต่ละหน้าต่างแล้วกดปุ่มใดก็ได้เพื่อปิด)

**ทางเลือกเสริม:** ถ้าต้องการให้ภาพที่วางไว้ในโฟลเดอร์ `OCR\inbox` โดยตรง (นอกเหนือจากการลากวาง
ผ่านหน้าเว็บ) ถูกประมวลผลอัตโนมัติ ให้ดับเบิลคลิก **`start_watcher.bat`** เพิ่มด้วย ฟีเจอร์นี้เป็นทางเลือก
เสริม — การอัปโหลดผ่านหน้าเว็บทำงานได้โดยไม่ต้องใช้ตัวนี้

---

## Option 2: ติดตั้งแบบละเอียดทีละขั้นตอน (ใช้เทอร์มินัล)

ใช้วิธีนี้หากต้องการเห็นทุกขั้นตอนอย่างละเอียด, สคริปต์ `.bat` ใช้ไม่ได้บนเครื่องของคุณ, หรือคุณใช้ระบบ
ปฏิบัติการอื่น คำสั่งทั้งหมดด้านล่างพิมพ์ในเทอร์มินัล — บน Windows อาจใช้ **PowerShell**,
**Command Prompt**, หรือ **Git Bash** ก็ได้ แต่ละขั้นตอนจะระบุว่าต้องอยู่ในโฟลเดอร์ไหน

### 1. ติดตั้ง Backend

เปิดเทอร์มินัล **ในโฟลเดอร์หลักของโปรเจกต์** แล้วรัน:

```
cd backend
python -m venv .venv
```

เปิดใช้งาน virtual environment — คำสั่งจะต่างกันไปตามเชลล์ที่ใช้:

```
.venv\Scripts\activate          (Command Prompt)
.venv\Scripts\Activate.ps1      (PowerShell)
source .venv/Scripts/activate   (Git Bash)
```

คุณควรเห็นคำว่า `(.venv)` ขึ้นที่หน้าพรอมต์ของเทอร์มินัล จากนั้น ในโฟลเดอร์ `backend` เดิม
รันคำสั่ง:

```
pip install -r requirements.txt
```

⚠️ คำสั่งนี้จะดาวน์โหลด PyTorch + EasyOCR (ประมาณ 1-2 GB) ในครั้งแรก อาจใช้เวลาหลายนาที
อย่าเพิ่งปิดเทอร์มินัลระหว่างที่กำลังรัน

### 2. เริ่ม Backend

อยู่ในโฟลเดอร์ `backend` เหมือนเดิม โดยเปิดใช้งาน virtual environment ไว้:

```
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

เปิดเทอร์มินัลนี้ค้างไว้ คุณควรเห็นข้อความ `Application startup complete.` และ
`Uvicorn running on http://127.0.0.1:8000` ลองตรวจสอบว่าทำงานถูกต้องโดยเปิด
`http://localhost:8000/api/health` ในเบราว์เซอร์ — ควรขึ้น `{"status":"ok"}`

### 3. ติดตั้งและเริ่ม Frontend

เปิดเทอร์มินัล **หน้าต่างใหม่แยกต่างหาก** ในโฟลเดอร์หลักของโปรเจกต์:

```
cd frontend
npm install
node server.js
```

เปิดเทอร์มินัลนี้ค้างไว้เช่นกัน ควรขึ้นข้อความ `Frontend running at http://localhost:3000`

### 4. เปิดแอป

ไปที่ `http://localhost:3000` ในเบราว์เซอร์ ต้องเปิดเทอร์มินัลทั้งสองหน้าต่าง (backend และ
frontend) ค้างไว้ระหว่างใช้งานแอป

### 5. (ทางเลือกเสริม) Folder watcher

หากต้องการวางภาพลงในโฟลเดอร์ `OCR/inbox` โดยตรงแล้วให้ประมวลผลอัตโนมัติ (นอกเหนือจากการใช้
พื้นที่อัปโหลดบนหน้าเว็บ) ให้เปิดเทอร์มินัล **หน้าต่างที่สาม** ในโฟลเดอร์หลักของโปรเจกต์:

```
cd backend
.venv\Scripts\activate
python -m app.watcher
```

---

## วิธีใช้งานแอปหลังจากรันขึ้นมาแล้ว

1. **อัปโหลดสลิป** — ลากและวางภาพ (หรือทั้งโฟลเดอร์) ลงบนพื้นที่อัปโหลด หรือคลิกเพื่อเลือกไฟล์
   แต่ละภาพจะถูก OCR และจัดโครงสร้างด้วย AI โดยอัตโนมัติ อาจใช้เวลา 10-30 วินาทีต่อภาพบน CPU
2. **ตรวจสอบตาราง** — ตรวจสอบข้อมูลที่ดึงออกมา ชื่อ / วันที่ / เวลา / จำนวนเงิน / โน้ต
   คลิกไอคอนดินสอที่แถวเพื่อแก้ไขค่าใดก็ได้ แล้วกดยืนยันหรือยกเลิก
3. **ชุดข้อมูลที่กำลังทำงาน (Working sets)** — ทุกอย่างที่อัปโหลดจะเข้าไปอยู่ใน "Current (unsaved)"
   ก่อน คลิก "Add more Set +" ในแถบด้านข้างถ้าต้องการชุดที่สองแยกต่างหากในเวลาเดียวกัน
   (เช่น อัปโหลดจากสองโฟลเดอร์พร้อมกัน)
4. **บันทึกหรือล้างข้อมูล (Save/Clear)** — เมื่อรายการดูถูกต้องแล้ว คลิก **Save Transactions**
   เพื่อบันทึกเป็นชุดถาวรที่ตั้งชื่อได้ (ระบบจะรัน AI ตรวจสอบซ้ำอีกครั้งและแจ้งเตือนหากพบความไม่ตรงกัน)
   คลิก **Clear shown** เพื่อล้างชุดที่ยังไม่บันทึกทั้งหมดแล้วเริ่มใหม่
5. **ชุดที่บันทึกแล้ว (แถบด้านข้าง)** — เปลี่ยนชื่อ ลบ ปักดาวรายการโปรด หรือจัดเรียงได้
   คลิกที่ชุดใดก็ได้เพื่อดูรายการ (ยังแก้ไขได้) พร้อมเวลาที่บันทึกและแก้ไขล่าสุด
6. **แท็บ Gallery** — แสดงภาพและรายละเอียดของสลิปทุกใบที่ประมวลผลแล้วในรูปแบบกริด
7. **แท็บ Zones** — เพื่อความแม่นยำที่มากขึ้น ให้ตั้งค่า "Zone Profile" สำหรับแต่ละแอปธนาคาร:
   อัปโหลดภาพตัวอย่างหนึ่งภาพ วาดกรอบรอบแต่ละช่องข้อมูล (ชื่อ/วันที่/เวลา/จำนวนเงิน) แล้วบันทึก
   การอัปโหลดครั้งต่อไปจะจับคู่โดยอัตโนมัติจากความคล้ายของภาพ — ไม่ต้องระบุว่าเป็นธนาคารอะไร
   ปุ่ม Export/Import ใช้สำรองหรือแชร์ค่าที่ตั้งไว้เป็นไฟล์เดียว ส่วน "Save as Default"
   จะทำให้ค่าเหล่านี้โหลดอัตโนมัติสำหรับการติดตั้งใหม่ทุกครั้ง
8. **กราฟ** — แสดงรายรับตามช่วงเวลาด้านล่างแท็บ Transactions กรองตามช่วงวันที่และสถานะได้
   (ถูกต้อง / รอตรวจสอบ / ต้องตรวจสอบ) พร้อมกล่องกาเครื่องหมายเลือกแสดง/ซ่อนแต่ละเส้น

---

## การแก้ปัญหา / ข้อผิดพลาดที่พบบ่อย

| อาการ | สาเหตุที่เป็นไปได้ / วิธีแก้ |
|---|---|
| อัปโหลดค้างที่สถานะ "pending" ตลอด หรือทุกสลิปไปอยู่ที่ "needs review" โดยไม่มีข้อมูลเลย | **Ollama ไม่ได้ทำงานอยู่** หรือยังไม่ได้รัน `ollama pull qwen2.5:1.5b` เปิดเทอร์มินัลแล้วรัน `ollama list` เพื่อเช็คว่ามีโมเดลอยู่หรือไม่ ถ้า Ollama เองไม่ทำงาน ให้รัน `ollama serve` |
| `pip install -r requirements.txt` ล้มเหลว หรือช้ามาก | ส่วนใหญ่เกิดจากอินเทอร์เน็ตช้าหรือไม่เสถียร (PyTorch เป็นไฟล์ขนาดใหญ่) ลองรันใหม่อีกครั้ง — pip จะดาวน์โหลดต่อจากที่ค้างไว้ ตรวจสอบว่าใช้ Python 3.10 ขึ้นไป (`python --version`) |
| ขึ้น `'python' is not recognized` / `'node' is not recognized` | ยังไม่ได้ติดตั้งโปรแกรมที่จำเป็น หรือไม่ได้เพิ่มลงใน PATH ของระบบ ให้ติดตั้งใหม่และติ๊กช่อง "Add to PATH" ระหว่างติดตั้ง แล้ว**เปิดหน้าต่างเทอร์มินัลใหม่** (การเปลี่ยนแปลง PATH จะไม่มีผลกับเทอร์มินัลที่เปิดค้างไว้อยู่แล้ว) |
| Backend พังตอนเริ่มทำงานด้วย error เกี่ยวกับ Unicode/encoding บน Windows | ตรวจสอบว่าตั้งค่า `PYTHONIOENCODING=utf-8` ก่อนรัน uvicorn — ไฟล์ `start_backend.bat` ตั้งค่านี้ให้อัตโนมัติอยู่แล้ว ถ้ารันเองด้วยมือ ให้ตั้งค่าเอง: `set PYTHONIOENCODING=utf-8` (Command Prompt) หรือ `$env:PYTHONIOENCODING="utf-8"` (PowerShell) ก่อนรันคำสั่ง `uvicorn` |
| เบราว์เซอร์ไม่ขึ้นอะไรเลย / connection refused ที่ `localhost:3000` | ไม่มีอะไรทำงานอยู่ที่พอร์ต 3000 เลย — เซิร์ฟเวอร์ frontend ไม่ได้เริ่มทำงาน (หรือพังไปแล้ว) ให้ไล่เช็คตามลำดับนี้: **(1)** ดูหน้าต่าง FRONTEND — ขึ้นข้อความ `[ERROR] Frontend dependencies not installed. Run setup.bat first.` หรือไม่ ถ้าใช่ ให้รัน `setup.bat` (หรือ `cd frontend && npm install`) **(2)** หน้าต่าง FRONTEND ยังเปิดอยู่ไหม ถ้าถูกปิดไป (โดยคุณเองหรืออย่างอื่น) เซิร์ฟเวอร์ก็หยุดทำงานทันที — แค่ดับเบิลคลิก `start_frontend.bat` ใหม่ (หรือ `start_all.bat`) **(3)** ถ้าหน้าต่างเปิดอยู่แต่ไม่ขึ้นบรรทัด `Frontend running at http://localhost:3000` ให้รันเองด้วยมือเพื่อดู error จริง: `cd frontend` แล้วตามด้วย `node server.js` — อ่านข้อความที่ขึ้นมา **(4)** เช็คหน้าต่าง BACKEND แบบเดียวกัน เพราะ frontend เรียก API ผ่าน backend และบางหน้าจะใช้งานไม่ได้จนกว่า backend จะพร้อม — เปิด `http://localhost:8000/api/health` เพื่อเช็คว่าขึ้น `{"status":"ok"}` **(5)** ถ้ายัง connection refused โดยไม่มีหน้าต่างไหนเปิดอยู่เลย อาจมีบางอย่าง (แอนตี้ไวรัส หรือโปรเซสเก่าที่ค้างอยู่) บล็อกพอร์ตนั้นอยู่ — ดูแถวพอร์ตถูกใช้งานด้านล่าง |
| พอร์ต (`8000` หรือ `3000`) ถูกใช้งานอยู่แล้ว | มีแอปนี้อีกชุดหนึ่ง (หรือโปรแกรมอื่น) กำลังใช้พอร์ตนั้นอยู่ บน Windows ให้หาและปิดมันด้วยวิธีนี้: เปิด Command Prompt แล้วรัน `netstat -ano | findstr :3000` (หรือ `:8000`) — คอลัมน์สุดท้ายคือ PID จากนั้นรัน `taskkill /PID <เลขนั้น> /F` เพื่อปิดโปรเซสนั้น แล้วเปิดแอปใหม่อีกครั้ง ส่วนใหญ่มักเป็นเพราะ `start_all.bat` ชุดก่อนหน้ายังทำงานค้างอยู่เบื้องหลัง — ลองเช็คว่ามีหน้าต่าง BACKEND/FRONTEND เก่าค้างอยู่หรือไม่ก่อน |
| วันที่/เวลาผิดสำหรับสลิปของธนาคารบางแห่ง | โมเดล AI ขนาดเล็กที่รันในเครื่องอาจอ่านข้อความ OCR ผิดพลาดได้ (เดือนภาษาไทย, เวลาแบบ 12 ชั่วโมง ฯลฯ) — แก้ไขค่าที่ตารางได้โดยตรงเสมอ ถ้าธนาคารใดผิดพลาดซ้ำ ๆ การตั้งค่า Zone Profile สำหรับธนาคารนั้น (ดูที่แท็บ Zones) มักจะช่วยได้มาก |

---

## โครงสร้างโปรเจกต์

```
setup.bat              ติดตั้งครั้งแรก (Option 1)
start_all.bat           เปิด backend + frontend + เปิดเบราว์เซอร์อัตโนมัติ (Option 1)
start_backend.bat       เปิดเฉพาะ backend
start_frontend.bat      เปิดเฉพาะ frontend
start_watcher.bat       ทางเลือกเสริม: ประมวลผลไฟล์ที่วางใน OCR/inbox อัตโนมัติ

backend/                แอป FastAPI, ฐานข้อมูล SQLite, ไปป์ไลน์ OCR + AI
  app/pipeline/          OCR (EasyOCR), LLM (Ollama), การจับคู่/ครอปโซน
  app/routes/            REST API endpoints
  data/                  ฐานข้อมูล SQLite อยู่ที่นี่ (ไม่ถูกอัปขึ้น git)

frontend/               เว็บเซิร์ฟเวอร์ Express + แดชบอร์ด JS/HTML/CSS ธรรมดา

OCR/                    โฟลเดอร์ทำงานสำหรับภาพ (ไม่ถูกอัปขึ้น git)
  inbox/                 วางภาพที่นี่สำหรับ folder watcher (ทางเลือกเสริม)
  uploads/                พื้นที่พักไฟล์ชั่วคราวสำหรับการอัปโหลดผ่านเว็บ
  processed/              ภาพที่ประมวลผลสำเร็จ จัดเรียงตามเดือน
  needs_review/           ภาพที่ OCR/AI ประมวลผลไม่สำเร็จ
  zone_samples/           ภาพตัวอย่างสำหรับตั้งค่า Zone Profiles
```

## การตั้งค่า

ตัวแปรสภาพแวดล้อม (environment variables) ฝั่ง backend ทั้งหมดเป็นทางเลือกเสริม:

- `OLLAMA_HOST` — ค่าเริ่มต้น `http://localhost:11434`
- `OLLAMA_MODEL` — ค่าเริ่มต้น `qwen2.5:1.5b` (เปลี่ยนเป็นโมเดลอื่นที่ดึงไว้แล้วเพื่อเทียบความแม่นยำได้
  — ไม่ต้องแก้โค้ด)

## ข้อมูลและความเป็นส่วนตัว

ฐานข้อมูล SQLite (`backend/data/app.db`), ภาพสลิปทั้งหมด (`OCR/`), และไฟล์ seed ของ zone
profile ใด ๆ จะ**ไม่ถูกอัปขึ้น git** (ดูที่ `.gitignore`) เนื่องจากมีชื่อจริง จำนวนเงิน และเลขบัญชี
บางส่วนอยู่ในนั้น มีเพียงโค้ดของแอปพลิเคชันเท่านั้นที่ควรแชร์/คอมมิต — ห้ามอัปโฟลเดอร์
`backend/data/` หรือภาพสลิปจริงของคุณขึ้นที่สาธารณะเด็ดขาด
