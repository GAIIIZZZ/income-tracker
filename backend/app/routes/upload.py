from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from ..config import UPLOAD_STAGING_DIR
from ..pipeline.organizer import run_pipeline

router = APIRouter()

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


@router.post("/upload")
async def upload_image(file: UploadFile, draft_slot: int = Form(1)):
    suffix = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(400, f"Unsupported file type: {suffix}")

    UPLOAD_STAGING_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_STAGING_DIR / file.filename
    counter = 1
    while dest.exists():
        dest = UPLOAD_STAGING_DIR / f"{Path(file.filename).stem}_{counter}{suffix}"
        counter += 1

    contents = await file.read()
    dest.write_bytes(contents)

    record = await run_in_threadpool(run_pipeline, str(dest), draft_slot)
    return record
