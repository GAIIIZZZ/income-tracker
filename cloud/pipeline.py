"""OCR (EasyOCR, local) + LLM structuring (Groq API, free hosted) for the Streamlit cloud alt.

Ported from backend/app/pipeline/ocr.py and llm.py. The only real difference from the local
version: _call_llm() talks to Groq's hosted API instead of a local Ollama server, since a free
web host has no way to run Ollama itself. Everything else (system prompt, deterministic date/
time regex fixes for the small model's known weaknesses) is unchanged.
"""

import json
import os
import re

import easyocr
import requests
import streamlit as st

GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
OCR_LANGUAGES = ["th", "en"]
LOW_CONFIDENCE_THRESHOLD = 0.4

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


@st.cache_resource(show_spinner="Loading OCR model (first time only, ~1-2 GB download)...")
def get_reader() -> easyocr.Reader:
    return easyocr.Reader(OCR_LANGUAGES, gpu=False, verbose=False)


def extract_text(image_path: str) -> tuple[str, float]:
    """Returns (raw_text, avg_confidence) for a full image on disk."""
    results = get_reader().readtext(image_path)
    if not results:
        return "", 0.0
    lines = [text for (_, text, _) in results]
    confidences = [conf for (_, _, conf) in results]
    return "\n".join(lines), sum(confidences) / len(confidences)


def _call_llm(prompt: str) -> str:
    api_key = st.secrets.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise LLMParseError(
            "GROQ_API_KEY is not set. Add it to .streamlit/secrets.toml (local) or the app's "
            "Secrets settings (Streamlit Community Cloud)."
        )
    resp = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _normalize_to_buddhist_era(date_str):
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
_MONTH_PATTERN = "|".join(re.escape(k) for k in sorted(THAI_MONTHS, key=len, reverse=True))
_THAI_DATE_RE = re.compile(rf"(\d{{1,2}})\s*[.\-/]?\s*({_MONTH_PATTERN})\s*[.\-/]?\s*(\d{{2,4}})")


def extract_thai_date(text: str):
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
    if year < 100:
        year += 2500
    elif year < 2400:
        year += 543
    return f"{year:04d}-{month:02d}-{day:02d}"


ENGLISH_MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}
_ENGLISH_MONTH_PATTERN = "|".join(re.escape(k) for k in sorted(ENGLISH_MONTHS, key=len, reverse=True))
_ENGLISH_DATE_RE = re.compile(
    rf"(\d{{1,2}})\s*[.\-/]?\s*({_ENGLISH_MONTH_PATTERN})\s*[.\-/]?\s*(\d{{2,4}})", re.IGNORECASE
)


def extract_english_date(text: str):
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
    return extract_thai_date(text) or extract_english_date(text)


_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")


def _normalize_time(time_str):
    if not time_str:
        return time_str
    match = re.match(r"^(\d{1,2}):(\d{2})$", str(time_str).strip())
    if not match:
        return time_str
    hour = int(match.group(1)) % 24
    return f"{hour:02d}:{match.group(2)}"


def extract_time(text: str):
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


def structure(raw_text: str) -> dict:
    """Returns a structured dict per SYSTEM_PROMPT's schema. Raises LLMParseError on failure."""
    prompt = f"{SYSTEM_PROMPT}\n\nOCR text:\n{raw_text}\n\nJSON output:"

    regex_date = extract_date(raw_text)
    regex_time = extract_time(raw_text)

    last_error = None
    for _attempt in range(2):
        try:
            raw_response = _call_llm(prompt)
            data = json.loads(raw_response)
            data["transaction_date"] = regex_date or _normalize_to_buddhist_era(data.get("transaction_date"))
            data["transaction_time"] = regex_time or _normalize_time(data.get("transaction_time"))
            data["_raw_response"] = raw_response
            return data
        except (json.JSONDecodeError, requests.RequestException, KeyError) as exc:
            last_error = exc
            prompt = (
                f"{SYSTEM_PROMPT}\n\nOCR text:\n{raw_text}\n\n"
                "Your previous response was not valid JSON. Respond with ONLY the JSON object, "
                "no markdown, no explanation.\n\nJSON output:"
            )

    raise LLMParseError(str(last_error))


def process_image(image_path: str) -> dict:
    """Runs OCR -> LLM for one image, returns a result dict ready for the review table."""
    raw_text, ocr_confidence = extract_text(image_path)

    if not raw_text.strip():
        return {
            "sender_name": None, "transaction_date": None, "transaction_time": None,
            "amount": None, "raw_ocr_text": "", "confidence": 0.0,
            "status": "needs_review", "llm_raw_response": None,
        }

    try:
        structured = structure(raw_text)
        llm_raw = structured.get("_raw_response")
    except LLMParseError:
        structured = {}
        llm_raw = None

    needs_review = not structured or ocr_confidence < LOW_CONFIDENCE_THRESHOLD
    return {
        "sender_name": structured.get("sender_name"),
        "transaction_date": structured.get("transaction_date"),
        "transaction_time": structured.get("transaction_time"),
        "amount": structured.get("amount"),
        "raw_ocr_text": raw_text,
        "confidence": ocr_confidence,
        "status": "needs_review" if needs_review else "pending",
        "llm_raw_response": llm_raw,
    }
