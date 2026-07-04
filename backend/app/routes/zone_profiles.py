import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from ..config import ZONE_PROFILES_SEED_PATH, ZONE_SAMPLES_DIR
from ..db import get_conn
from ..pipeline import zonal, zone_seed

router = APIRouter()

ALLOWED_FIELDS = {"sender_name", "transaction_date", "transaction_time", "amount"}
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


@router.get("/zone-profiles")
def list_zone_profiles():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM zone_profiles ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


@router.post("/zone-profiles")
async def create_zone_profile(
    name: str = Form(...),
    identifier_keywords: str = Form(""),
    zones_json: str = Form(...),
    sample_image: Optional[UploadFile] = File(None),
):
    if not name.strip():
        raise HTTPException(400, "Name is required")
    if sample_image is None or not sample_image.filename:
        raise HTTPException(400, "A sample image is required for visual matching")

    try:
        zones = json.loads(zones_json)
    except json.JSONDecodeError:
        raise HTTPException(400, "zones_json must be valid JSON")

    if not isinstance(zones, list) or not zones:
        raise HTTPException(400, "At least one zone is required")
    for zone in zones:
        if zone.get("field") not in ALLOWED_FIELDS:
            raise HTTPException(400, f"Invalid zone field: {zone.get('field')}")
        for key in ("x", "y", "width", "height"):
            if not isinstance(zone.get(key), (int, float)):
                raise HTTPException(400, f"Zone missing numeric '{key}'")

    suffix = "." + sample_image.filename.rsplit(".", 1)[-1].lower() if "." in sample_image.filename else ""
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(400, f"Unsupported sample image type: {suffix}")
    ZONE_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    dest = ZONE_SAMPLES_DIR / sample_image.filename
    counter = 1
    while dest.exists():
        dest = ZONE_SAMPLES_DIR / f"{Path(sample_image.filename).stem}_{counter}{suffix}"
        counter += 1
    contents = await sample_image.read()
    dest.write_bytes(contents)
    sample_path = str(dest)
    image_hash = zonal.compute_image_hash(sample_path)

    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO zone_profiles (name, identifier_keywords, image_hash, sample_image_path, zones_json)
               VALUES (?, ?, ?, ?, ?)""",
            (name.strip(), identifier_keywords.strip(), image_hash, sample_path, json.dumps(zones)),
        )
        profile_id = cur.lastrowid
        row = conn.execute("SELECT * FROM zone_profiles WHERE id = ?", (profile_id,)).fetchone()
        return dict(row)


@router.delete("/zone-profiles/{profile_id}")
def delete_zone_profile(profile_id: int):
    with get_conn() as conn:
        existing = conn.execute("SELECT id FROM zone_profiles WHERE id = ?", (profile_id,)).fetchone()
        if not existing:
            raise HTTPException(404, "Zone profile not found")
        conn.execute("DELETE FROM zone_profiles WHERE id = ?", (profile_id,))
        return {"deleted": profile_id}


@router.get("/zone-profiles/export")
def export_zone_profiles():
    with get_conn() as conn:
        data = zone_seed.export_profiles(conn)
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": "attachment; filename=zone_profiles_export.json"},
    )


@router.post("/zone-profiles/import")
async def import_zone_profiles(file: UploadFile = File(...)):
    contents = await file.read()
    try:
        data = json.loads(contents)
    except json.JSONDecodeError:
        raise HTTPException(400, "Not a valid JSON file")

    with get_conn() as conn:
        imported = zone_seed.import_profiles(conn, data)
    return {"imported": imported}


@router.post("/zone-profiles/save-as-seed")
def save_zone_profiles_as_seed():
    """Writes the current zone profiles to the bundled seed file, so a fresh install of
    this project (this machine or another) auto-loads them on first startup."""
    with get_conn() as conn:
        data = zone_seed.export_profiles(conn)
    if not data["profiles"]:
        raise HTTPException(400, "No zone profiles to save")
    ZONE_PROFILES_SEED_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"saved": len(data["profiles"]), "path": str(ZONE_PROFILES_SEED_PATH)}
