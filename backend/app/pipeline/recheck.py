"""Re-runs LLM extraction on a transaction's stored OCR text as a save-time sanity check."""

from typing import Optional

from . import llm


def _normalize(value) -> str:
    return "" if value is None else str(value).strip().lower()


def _amounts_differ(a, b, tolerance: float = 0.01) -> bool:
    if a is None or b is None:
        return a != b
    try:
        return abs(float(a) - float(b)) > tolerance
    except (TypeError, ValueError):
        return True


def recheck_transaction(row: dict) -> tuple[str, Optional[str]]:
    """Returns (recheck_status, recheck_note). Status is 'match', 'mismatch', or 'skipped'."""
    raw_text = row.get("raw_ocr_text")
    if not raw_text or not raw_text.strip():
        return "skipped", None

    try:
        fresh = llm.structure(raw_text)
    except llm.LLMParseError as exc:
        return "skipped", f"recheck failed: {exc}"

    diffs = []
    if _normalize(fresh.get("sender_name")) != _normalize(row.get("sender_name")):
        diffs.append(f"name: '{row.get('sender_name')}' vs '{fresh.get('sender_name')}'")
    if _normalize(fresh.get("transaction_date")) != _normalize(row.get("transaction_date")):
        diffs.append(f"date: '{row.get('transaction_date')}' vs '{fresh.get('transaction_date')}'")
    if _amounts_differ(fresh.get("amount"), row.get("amount")):
        diffs.append(f"amount: {row.get('amount')} vs {fresh.get('amount')}")

    if diffs:
        return "mismatch", "Second AI pass disagreed on " + "; ".join(diffs)
    return "match", None
