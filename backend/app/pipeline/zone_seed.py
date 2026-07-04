"""Shared import/export logic for zone profiles, used by the API endpoints, the manual
import button, and auto-seeding a fresh database from a bundled seed file. The export
format embeds sample images as base64 so a single JSON file is fully self-contained and
portable between installations."""

import base64
import json
from pathlib import Path

from ..config import ZONE_SAMPLES_DIR
from . import zonal

FORMAT_VERSION = 2


def export_profiles(conn) -> dict:
    rows = [dict(r) for r in conn.execute("SELECT * FROM zone_profiles").fetchall()]
    profiles = []
    for row in rows:
        sample_b64 = None
        if row.get("sample_image_path"):
            path = Path(row["sample_image_path"])
            if path.exists():
                mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
                encoded = base64.b64encode(path.read_bytes()).decode("ascii")
                sample_b64 = f"data:{mime};base64,{encoded}"
        profiles.append({
            "name": row["name"],
            "identifier_keywords": row.get("identifier_keywords") or "",
            "image_hash": row.get("image_hash"),
            "zones": json.loads(row["zones_json"]),
            "sample_image_base64": sample_b64,
        })
    return {"version": FORMAT_VERSION, "profiles": profiles}


def import_profiles(conn, data: dict) -> int:
    """Inserts zone profiles from an export/seed JSON dict. Additive — does not touch or
    de-duplicate existing profiles. Returns the number imported."""
    imported = 0
    for profile in data.get("profiles", []):
        name = profile.get("name")
        zones = profile.get("zones")
        if not name or not zones:
            continue
        identifier_keywords = profile.get("identifier_keywords") or ""

        sample_path = None
        b64 = profile.get("sample_image_base64")
        if b64:
            sample_path = _save_base64_sample(name, b64)

        image_hash = profile.get("image_hash")
        if not image_hash and sample_path:
            # Older export format (v1) predates image_hash — compute it from the sample.
            try:
                image_hash = zonal.compute_image_hash(sample_path)
            except Exception:
                image_hash = None

        conn.execute(
            """INSERT INTO zone_profiles (name, identifier_keywords, image_hash, sample_image_path, zones_json)
               VALUES (?, ?, ?, ?, ?)""",
            (name, identifier_keywords, image_hash, sample_path, json.dumps(zones)),
        )
        imported += 1
    return imported


def _save_base64_sample(name: str, data_url: str) -> str:
    ZONE_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    header, _, b64data = data_url.partition(",")
    ext = ".png" if "png" in header else ".webp" if "webp" in header else ".jpg"
    raw = base64.b64decode(b64data)

    safe_name = "".join(c if c.isalnum() else "_" for c in name) or "profile"
    dest = ZONE_SAMPLES_DIR / f"{safe_name}_seed{ext}"
    counter = 1
    while dest.exists():
        dest = ZONE_SAMPLES_DIR / f"{safe_name}_seed_{counter}{ext}"
        counter += 1
    dest.write_bytes(raw)
    return str(dest)
