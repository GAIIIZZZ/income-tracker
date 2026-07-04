"""Matches an uploaded slip to a calibrated zone profile and crops/OCRs its fields.

Matching is primarily visual: each profile stores a perceptual hash of its whole sample
image, and a new upload is matched by comparing hashes — this doesn't require the bank's
name to appear anywhere as OCR-able text, since many banking apps only show a logo.
An identifier keyword is still supported as an optional, stronger signal for profiles
where the OCR text does reliably contain something distinctive."""

import json
from typing import Optional

from PIL import Image

from . import ocr

HASH_SIZE = 16  # 16x16 -> 256-bit hash; finer than the usual 8x8 to tell similar bank-app
                # screens apart (e.g. a bank's transfer vs. bill-payment confirmation screens).
DEFAULT_HASH_THRESHOLD = 50  # max Hamming distance (out of 256 bits) still considered a match
DEFAULT_HASH_MARGIN = 15     # best match must beat the runner-up by at least this many bits —
                             # some visually-similar bank apps (e.g. two banks both using a
                             # plain white/green confirmation screen) can land within a few bits
                             # of each other, so a close race is treated as "don't know" rather
                             # than guessing, since a wrong zone profile is worse than none.


def compute_image_hash(image) -> str:
    """Average-hash of the whole image: resize small, grayscale, threshold against the mean.
    Robust to minor resizing/recompression; sensitive to cropping/aspect-ratio changes, which
    is fine since a profile's sample and future uploads come from the same app's screenshots."""
    if isinstance(image, str):
        image = Image.open(image)
    gray = image.convert("L").resize((HASH_SIZE, HASH_SIZE), Image.LANCZOS)
    pixels = list(gray.getdata())
    avg = sum(pixels) / len(pixels)
    return "".join("1" if p > avg else "0" for p in pixels)


def hamming_distance(hash_a: str, hash_b: str) -> int:
    if not hash_a or not hash_b or len(hash_a) != len(hash_b):
        return len(hash_a or hash_b or "")
    return sum(a != b for a, b in zip(hash_a, hash_b))


def match_profile(
    image_path: str,
    raw_text: str,
    profiles: list[dict],
    hash_threshold: int = DEFAULT_HASH_THRESHOLD,
    hash_margin: int = DEFAULT_HASH_MARGIN,
) -> Optional[dict]:
    """Matches by identifier keyword first (a strong, unambiguous signal when present and
    non-empty), then falls back to visual similarity to each profile's sample image. A visual
    match only counts if the best candidate is both under the distance threshold AND clearly
    ahead of the second-best candidate — a close race between two profiles is treated as no
    match at all, since applying the wrong bank's zone crops is worse than applying none."""
    text_lower = (raw_text or "").lower()
    for profile in profiles:
        keywords = [k.strip().lower() for k in (profile.get("identifier_keywords") or "").split(",") if k.strip()]
        if keywords and any(k in text_lower for k in keywords):
            return profile

    candidates = [p for p in profiles if p.get("image_hash")]
    if not candidates:
        return None

    image_hash = compute_image_hash(image_path)
    ranked = sorted(
        ((hamming_distance(image_hash, p["image_hash"]), p) for p in candidates),
        key=lambda pair: pair[0],
    )
    best_distance, best_profile = ranked[0]
    if best_distance > hash_threshold:
        return None
    if len(ranked) > 1:
        runner_up_distance = ranked[1][0]
        if runner_up_distance - best_distance < hash_margin:
            return None
    return best_profile


def load_zones(profile: dict) -> list[dict]:
    return json.loads(profile["zones_json"])


def extract_zone_hints(image_path: str, zones: list[dict]) -> dict:
    """Crops each zone (fractions 0-1 of image size) and OCRs it. Returns {field: text}."""
    hints = {}
    with Image.open(image_path) as img:
        img = img.convert("RGB")
        width, height = img.size
        for zone in zones:
            left = max(0, int(zone["x"] * width))
            top = max(0, int(zone["y"] * height))
            right = min(width, int((zone["x"] + zone["width"]) * width))
            bottom = min(height, int((zone["y"] + zone["height"]) * height))
            if right <= left or bottom <= top:
                continue
            crop = img.crop((left, top, right, bottom))
            text, _confidence = ocr.extract_text_from_image(crop)
            text = text.strip()
            if text:
                hints[zone["field"]] = text
    return hints
