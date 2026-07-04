"""EasyOCR wrapper. The Reader is expensive to load, so it's created once and reused."""

import threading

import easyocr
import numpy as np

from ..config import OCR_LANGUAGES

_reader = None
_reader_lock = threading.Lock()


def get_reader() -> easyocr.Reader:
    global _reader
    if _reader is None:
        with _reader_lock:
            if _reader is None:
                _reader = easyocr.Reader(OCR_LANGUAGES, gpu=False, verbose=False)
    return _reader


def _summarize(results) -> tuple[str, float]:
    if not results:
        return "", 0.0
    lines = [text for (_, text, _) in results]
    confidences = [conf for (_, _, conf) in results]
    raw_text = "\n".join(lines)
    avg_confidence = sum(confidences) / len(confidences)
    return raw_text, avg_confidence


def extract_text(image_path: str) -> tuple[str, float]:
    """Returns (raw_text, avg_confidence) for a full image on disk."""
    reader = get_reader()
    results = reader.readtext(image_path)
    return _summarize(results)


def extract_text_from_image(image) -> tuple[str, float]:
    """Returns (raw_text, avg_confidence) for an in-memory PIL Image (e.g. a zone crop)."""
    reader = get_reader()
    results = reader.readtext(np.array(image))
    return _summarize(results)
