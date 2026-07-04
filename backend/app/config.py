import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OCR_ROOT = PROJECT_ROOT / "OCR"
INBOX_DIR = OCR_ROOT / "inbox"
PROCESSED_DIR = OCR_ROOT / "processed"
NEEDS_REVIEW_DIR = OCR_ROOT / "needs_review"

# Separate staging dir for API/website uploads, kept distinct from INBOX_DIR so the
# folder watcher (which watches INBOX_DIR) never races the upload endpoint on the same file.
UPLOAD_STAGING_DIR = OCR_ROOT / "uploads"

# Sample slip images kept for reference/editing of zone-profile calibrations.
ZONE_SAMPLES_DIR = OCR_ROOT / "zone_samples"

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "app.db"

# If present, its zone profiles are auto-loaded into a fresh (empty zone_profiles) database
# on startup — lets calibrated profiles ship with the project for new installs.
ZONE_PROFILES_SEED_PATH = Path(__file__).resolve().parent.parent / "zone_profiles_seed.json"

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")

OCR_LANGUAGES = ["th", "en"]

LOW_CONFIDENCE_THRESHOLD = 0.4
