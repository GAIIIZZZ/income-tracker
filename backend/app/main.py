from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import NEEDS_REVIEW_DIR, PROCESSED_DIR, UPLOAD_STAGING_DIR, ZONE_SAMPLES_DIR
from .db import init_db
from .routes import batches, clear, summary, transactions, upload, zone_profiles

app = FastAPI(title="Receipt OCR Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    NEEDS_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_STAGING_DIR.mkdir(parents=True, exist_ok=True)
    ZONE_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)


app.include_router(transactions.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(batches.router, prefix="/api")
app.include_router(clear.router, prefix="/api")
app.include_router(summary.router, prefix="/api")
app.include_router(zone_profiles.router, prefix="/api")

ZONE_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/images/processed", StaticFiles(directory=str(PROCESSED_DIR)), name="processed_images")
app.mount("/images/needs_review", StaticFiles(directory=str(NEEDS_REVIEW_DIR)), name="needs_review_images")
app.mount("/images/zone_samples", StaticFiles(directory=str(ZONE_SAMPLES_DIR)), name="zone_sample_images")


@app.get("/api/health")
def health():
    return {"status": "ok"}
