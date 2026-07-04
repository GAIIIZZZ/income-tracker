"""Sends OCR'd bank-transfer-slip text to a local Ollama model and gets back structured JSON."""

import json
import re

import requests

from ..config import OLLAMA_HOST, OLLAMA_MODEL

SYSTEM_PROMPT = """You are a bank transfer slip parsing assistant. You will be given raw OCR
text from a Thai or English bank transfer slip. The text may contain OCR errors. These slips
always list TWO names: the SENDER (top, usually labeled "จาก" / "From") and the RECEIVER
(bottom, usually labeled "ไปยัง" / "To"). Extract ONLY the sender's (top) name — never the
receiver's (bottom) name. Respond with ONLY a JSON object, no other text.

Thai month names/abbreviations, for reference (do not confuse ones that share a syllable,
e.g. มี.ค.=March vs มิ.ย.=June, or พ.ค.=May vs พ.ย.=November):
มกราคม/ม.ค.=01  กุมภาพันธ์/ก.พ.=02  มีนาคม/มี.ค.=03  เมษายน/เม.ย.=04  พฤษภาคม/พ.ค.=05
มิถุนายน/มิ.ย.=06  กรกฎาคม/ก.ค.=07  สิงหาคม/ส.ค.=08  กันยายน/ก.ย.=09  ตุลาคม/ต.ค.=10
พฤศจิกายน/พ.ย.=11  ธันวาคม/ธ.ค.=12

Schema:
{
  "sender_name": string or null (the TOP/sender name only),
  "transaction_date": string "YYYY-MM-DD" or null, using the Thai Buddhist Era (พ.ศ.) year —
     if the slip shows a Gregorian year (e.g. 2026), convert it to Buddhist Era by ADDING 543
     (2026 -> 2569); if the slip already shows a Buddhist Era year (e.g. 2569), keep it as-is,
  "transaction_time": string "HH:MM" (24-hour) or null,
  "amount": number or null (the transferred amount, not the fee)
}

Example input:
โอนเงินสำเร็จ
26 มิ.ย. 2569 16:46
จาก
น.ส. กัลยา ใจดี
กรุงไทย xxx-x-x9200-x
ไปยัง
น.ส. สุภาพร วงศ์บุปผา
กสิกรไทย xxx-x-x4727-x
จำนวนเงิน
340.00 บาท
ค่าธรรมเนียม
0.00 บาท

Example output:
{"sender_name": "น.ส. กัลยา ใจดี", "transaction_date": "2569-06-26", "transaction_time": "16:46", "amount": 340.0}
"""


class LLMParseError(Exception):
    pass


def _call_ollama(prompt: str) -> str:
    resp = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "format": "json",
            "stream": False,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["response"]


def _normalize_to_buddhist_era(date_str):
    """Small models are unreliable at +543 arithmetic, so enforce it in code: any 4-digit
    year below 2400 is clearly Gregorian and gets converted to Buddhist Era. Also guards
    against the model emitting DD-MM-YYYY instead of the requested YYYY-MM-DD — reinterpreted
    rather than silently passed through un-validated (day-first, matching Thai convention)."""
    if not date_str:
        return date_str
    text = str(date_str).strip()

    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", text)
    if match:
        year = int(match.group(1))
        if year < 2400:
            year += 543
        return f"{year:04d}-{match.group(2)}-{match.group(3)}"

    match = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", text)
    if match:
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if year < 2400:
            year += 543
        return f"{year:04d}-{month:02d}-{day:02d}"

    return date_str


# Small models also unreliably convert Thai month names to numbers (e.g. confusing มิ.ย./June
# with มี.ค./March, both starting with the same syllable), so this mapping is enforced in code
# via regex against the raw OCR text instead of trusted from the model's own output.
THAI_MONTHS = {
    "มกราคม": 1, "ม.ค.": 1, "มค": 1,
    "กุมภาพันธ์": 2, "ก.พ.": 2, "กพ": 2,
    "มีนาคม": 3, "มี.ค.": 3, "มีค": 3,
    "เมษายน": 4, "เม.ย.": 4, "เมย": 4,
    "พฤษภาคม": 5, "พ.ค.": 5, "พค": 5,
    "มิถุนายน": 6, "มิ.ย.": 6, "มิย": 6,
    "กรกฎาคม": 7, "ก.ค.": 7, "กค": 7,
    "สิงหาคม": 8, "ส.ค.": 8, "สค": 8,
    "กันยายน": 9, "ก.ย.": 9, "กย": 9,
    "ตุลาคม": 10, "ต.ค.": 10, "ตค": 10,
    "พฤศจิกายน": 11, "พ.ย.": 11, "พย": 11,
    "ธันวาคม": 12, "ธ.ค.": 12, "ธค": 12,
}

# Longest keys first so full month names match before their short, more ambiguous abbreviations.
_MONTH_PATTERN = "|".join(re.escape(k) for k in sorted(THAI_MONTHS, key=len, reverse=True))
_THAI_DATE_RE = re.compile(rf"(\d{{1,2}})\s*[.\-/]?\s*({_MONTH_PATTERN})\s*[.\-/]?\s*(\d{{2,4}})")


def extract_thai_date(text: str):
    """Finds a 'DD <Thai month> YYYY' pattern in text and returns 'YYYY-MM-DD' in Buddhist
    Era, or None if no such pattern is found. Deterministic — bypasses the LLM entirely for
    the month component, which it gets wrong often enough to not be trusted."""
    if not text:
        return None
    match = _THAI_DATE_RE.search(text)
    if not match:
        return None
    day_str, month_text, year_str = match.groups()
    month = THAI_MONTHS.get(month_text)
    day = int(day_str)
    if not month or not (1 <= day <= 31):
        return None
    year = int(year_str)
    # A bare 2-digit year next to a Thai month name follows the Thai convention of a short
    # Buddhist Era year (e.g. "69" -> 2569), not a Gregorian shorthand.
    if year < 100:
        year += 2500
    elif year < 2400:
        year += 543
    return f"{year:04d}-{month:02d}-{day:02d}"


# Some slips (even from Thai banks) render in English, e.g. "3 Jul 26" — the small model
# reading these has been observed to swap the day and year entirely (not just misconvert
# the era), so this is extracted deterministically the same way as the Thai-month case.
ENGLISH_MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

_ENGLISH_MONTH_PATTERN = "|".join(re.escape(k) for k in sorted(ENGLISH_MONTHS, key=len, reverse=True))
_ENGLISH_DATE_RE = re.compile(
    rf"(\d{{1,2}})\s*[.\-/]?\s*({_ENGLISH_MONTH_PATTERN})\s*[.\-/]?\s*(\d{{2,4}})", re.IGNORECASE
)


def extract_english_date(text: str):
    """Finds a 'DD <English month> YY(YY)' pattern in text and returns 'YYYY-MM-DD' in
    Buddhist Era, or None. A bare 2-digit year here follows the Gregorian shorthand (e.g.
    "26" -> 2026), unlike the Thai case, since English month names signal Gregorian-style
    display on these slips."""
    if not text:
        return None
    match = _ENGLISH_DATE_RE.search(text)
    if not match:
        return None
    day_str, month_text, year_str = match.groups()
    month = ENGLISH_MONTHS.get(month_text.lower())
    day = int(day_str)
    if not month or not (1 <= day <= 31):
        return None
    year = int(year_str)
    if year < 100:
        year += 2000
    if year < 2400:
        year += 543
    return f"{year:04d}-{month:02d}-{day:02d}"


def extract_date(text: str):
    """Tries the Thai-month pattern first, then the English-month pattern."""
    return extract_thai_date(text) or extract_english_date(text)


_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")


def _normalize_time(time_str):
    """Fixes a common model bug: converting a 12-o'clock time (noon or midnight) and adding
    12 unconditionally, producing an invalid hour like 24 instead of wrapping to 0."""
    if not time_str:
        return time_str
    match = re.match(r"^(\d{1,2}):(\d{2})$", str(time_str).strip())
    if not match:
        return time_str
    hour = int(match.group(1)) % 24
    return f"{hour:02d}:{match.group(2)}"


def extract_time(text: str):
    """Finds an HH:MM pattern directly in OCR text and returns it normalized, or None.
    Preferred over trusting the model's own transcription, for the same reason as dates —
    small models mishandle the 12-o'clock edge case (see _normalize_time)."""
    if not text:
        return None
    match = _TIME_RE.search(text)
    if not match:
        return None
    minute = int(match.group(2))
    if not (0 <= minute <= 59):
        return None
    hour = int(match.group(1)) % 24
    return f"{hour:02d}:{minute:02d}"


ZONE_HINT_LABELS = {
    "sender_name": "Sender name",
    "transaction_date": "Date",
    "transaction_time": "Time",
    "amount": "Amount",
}


def _build_zone_hint_block(zone_hints) -> str:
    if not zone_hints:
        return ""
    lines = [
        f"- {ZONE_HINT_LABELS.get(field, field)} zone: {text}"
        for field, text in zone_hints.items()
        if text
    ]
    if not lines:
        return ""
    return (
        "\n\nAdditionally, these fields were cropped directly from known positions on this "
        "bank's slip template (a small, isolated image of just that field, so trust these over "
        "the full OCR text above if they disagree):\n" + "\n".join(lines)
    )


def structure(raw_text: str, zone_hints: dict = None) -> dict:
    """Returns a structured dict per SYSTEM_PROMPT's schema. Raises LLMParseError on failure.

    zone_hints, if given, is {field: cropped_text} from a matched zone profile (see zonal.py) —
    high-confidence text cropped from a known field position, passed as extra context."""
    hint_block = _build_zone_hint_block(zone_hints)
    prompt = f"{SYSTEM_PROMPT}\n\nOCR text:\n{raw_text}{hint_block}\n\nJSON output:"

    regex_date = None
    if zone_hints and zone_hints.get("transaction_date"):
        regex_date = extract_date(zone_hints["transaction_date"])
    if not regex_date:
        regex_date = extract_date(raw_text)

    regex_time = None
    if zone_hints and zone_hints.get("transaction_time"):
        regex_time = extract_time(zone_hints["transaction_time"])
    if not regex_time:
        regex_time = extract_time(raw_text)

    last_error = None
    for attempt in range(2):
        try:
            raw_response = _call_ollama(prompt)
            data = json.loads(raw_response)
            data["transaction_date"] = regex_date or _normalize_to_buddhist_era(data.get("transaction_date"))
            data["transaction_time"] = regex_time or _normalize_time(data.get("transaction_time"))
            data["_raw_response"] = raw_response
            return data
        except (json.JSONDecodeError, requests.RequestException, KeyError) as exc:
            last_error = exc
            prompt = (
                f"{SYSTEM_PROMPT}\n\nOCR text:\n{raw_text}{hint_block}\n\n"
                "Your previous response was not valid JSON. Respond with ONLY the JSON object, "
                "no markdown, no explanation.\n\nJSON output:"
            )

    raise LLMParseError(str(last_error))
