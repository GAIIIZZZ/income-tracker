"""Orchestrates OCR -> LLM -> DB insert -> file move for a single bank-slip image."""

import shutil
from datetime import datetime
from pathlib import Path

from ..config import LOW_CONFIDENCE_THRESHOLD, NEEDS_REVIEW_DIR, PROCESSED_DIR
from ..db import get_conn
from . import llm, ocr, zonal


def _unique_destination(dest_dir: Path, filename: str) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    candidate = dest_dir / filename
    if not candidate.exists():
        return candidate
    stem, suffix = candidate.stem, candidate.suffix
    counter = 1
    while candidate.exists():
        candidate = dest_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    return candidate


def run_pipeline(image_path: str, draft_slot: int = 1, transaction_type: str = "income") -> dict:
    image_path = str(image_path)
    filename = Path(image_path).name

    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO transactions (batch_id, draft_slot, transaction_type, source_image_path, status) VALUES (NULL, ?, ?, ?, 'pending')",
            (draft_slot, transaction_type, image_path),
        )
        transaction_id = cur.lastrowid

    try:
        raw_text, ocr_confidence = ocr.extract_text(image_path)
    except Exception as exc:
        print(f"[pipeline] OCR failed for {filename}: {exc}")
        with get_conn() as conn:
            conn.execute(
                "UPDATE transactions SET status = 'needs_review', updated_at = datetime('now', 'localtime') WHERE id = ?",
                (transaction_id,),
            )
        dest = _unique_destination(NEEDS_REVIEW_DIR, filename)
        shutil.move(image_path, dest)
        with get_conn() as conn:
            conn.execute(
                "UPDATE transactions SET processed_image_path = ? WHERE id = ?",
                (str(dest), transaction_id),
            )
        return _get_transaction(transaction_id)

    with get_conn() as conn:
        conn.execute(
            "UPDATE transactions SET raw_ocr_text = ?, confidence = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
            (raw_text, ocr_confidence, transaction_id),
        )

    structured = None
    llm_error = None
    if raw_text.strip():
        zone_hints = None
        with get_conn() as conn:
            profiles = [dict(r) for r in conn.execute("SELECT * FROM zone_profiles").fetchall()]
        matched_profile = zonal.match_profile(image_path, raw_text, profiles) if profiles else None
        if matched_profile:
            try:
                zone_hints = zonal.extract_zone_hints(image_path, zonal.load_zones(matched_profile))
                print(f"[pipeline] Matched zone profile '{matched_profile['name']}' for {filename}: {zone_hints}")
            except Exception as exc:
                print(f"[pipeline] Zone extraction failed for {filename}: {exc}")

        try:
            structured = llm.structure(raw_text, zone_hints, transaction_type)
        except llm.LLMParseError as exc:
            llm_error = str(exc)

    needs_review = (not raw_text.strip()) or structured is None or ocr_confidence < LOW_CONFIDENCE_THRESHOLD

    with get_conn() as conn:
        if structured is not None:
            conn.execute(
                """UPDATE transactions SET
                    sender_name = ?, transaction_date = ?, transaction_time = ?, amount = ?,
                    llm_raw_response = ?, status = ?, updated_at = datetime('now', 'localtime')
                   WHERE id = ?""",
                (
                    structured.get("sender_name"),
                    structured.get("transaction_date"),
                    structured.get("transaction_time"),
                    structured.get("amount"),
                    structured.get("_raw_response"),
                    "needs_review" if needs_review else "pending",
                    transaction_id,
                ),
            )
        else:
            print(f"[pipeline] LLM structuring failed for {filename}: {llm_error}")
            conn.execute(
                "UPDATE transactions SET status = 'needs_review', updated_at = datetime('now', 'localtime') WHERE id = ?",
                (transaction_id,),
            )

    row = _get_transaction(transaction_id)

    if needs_review:
        dest_dir = NEEDS_REVIEW_DIR
    else:
        month_key = (row.get("transaction_date") or datetime.now().strftime("%Y-%m-%d"))[:7]
        dest_dir = PROCESSED_DIR / month_key

    dest = _unique_destination(dest_dir, filename)
    shutil.move(image_path, dest)

    with get_conn() as conn:
        conn.execute(
            "UPDATE transactions SET processed_image_path = ? WHERE id = ?",
            (str(dest), transaction_id),
        )

    return _get_transaction(transaction_id)


def _get_transaction(transaction_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        return dict(row) if row else {}
