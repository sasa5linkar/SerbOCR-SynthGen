#!/usr/bin/env python3
"""
SerbOCR-SynthGen — Synthetic OCR dataset generator for Serbian (Cyrillic & Latin).

Usage:
    python generate.py --count 1000

Requirements:
    pip install pillow numpy cyrtranslit tqdm
"""

import argparse
import os
import random
import unicodedata
from pathlib import Path

import cyrtranslit
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
INPUT_DICTS = BASE_DIR / "input" / "dicts"
INPUT_FONTS = BASE_DIR / "input" / "fonts"
OUTPUT_DIR = BASE_DIR / "output"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TARGET_HEIGHT = 64          # px — optimised for modern VLMs
MARGIN = 10                 # horizontal padding per side (px)
BLUR_RANGE = (0.0, 2.0)    # Gaussian blur radius
SKEW_RANGE = (-5, 5)       # rotation in degrees
NOISE_STD = 15.0            # Gaussian noise standard deviation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_cyrillic(text: str) -> bool:
    """Return True if *text* contains at least one Cyrillic character."""
    return any("CYRILLIC" in unicodedata.name(c, "") for c in text if c.isalpha())


def load_words(dict_dir: Path) -> list[tuple[str, bool]]:
    """
    Load all words/lines from .txt files in *dict_dir*.

    Returns a list of ``(text, source_is_cyrillic)`` tuples.  When a file
    contains only Cyrillic text the Latin transliteration is appended so the
    two scripts are balanced.
    """
    entries: list[tuple[str, bool]] = []

    txt_files = sorted(dict_dir.glob("*.txt"))
    if not txt_files:
        raise FileNotFoundError(f"No .txt dictionary files found in {dict_dir}")

    for path in txt_files:
        lines = path.read_text(encoding="utf-8").splitlines()
        lines = [ln.strip() for ln in lines if ln.strip()]

        file_has_cyrillic = any(is_cyrillic(ln) for ln in lines)
        file_has_latin = any(
            not is_cyrillic(ln) and any(c.isalpha() for c in ln) for ln in lines
        )

        for line in lines:
            entries.append((line, is_cyrillic(line)))

        # If the entire file is Cyrillic-only, generate Latin counterparts.
        if file_has_cyrillic and not file_has_latin:
            for line in lines:
                latin = cyrtranslit.to_latin(line, "sr")
                entries.append((latin, False))

    return entries


def load_fonts(font_dir: Path) -> list[Path]:
    """Return a list of .ttf font paths from *font_dir*."""
    fonts = sorted(font_dir.glob("*.ttf"))
    if not fonts:
        raise FileNotFoundError(f"No .ttf font files found in {font_dir}")
    return fonts


def pick_font_size(font_path: Path, text: str, target_height: int) -> ImageFont.FreeTypeFont:
    """
    Binary-search for the largest font size whose rendered cap-height fits
    within *target_height* (minus vertical margins).
    """
    usable_h = target_height - 2 * 4  # 4 px top/bottom padding
    lo, hi = 8, target_height * 2

    img_tmp = Image.new("RGB", (1, 1))
    draw_tmp = ImageDraw.Draw(img_tmp)

    best_size = lo
    while lo <= hi:
        mid = (lo + hi) // 2
        try:
            fnt = ImageFont.truetype(str(font_path), mid)
        except OSError:
            break
        bbox = draw_tmp.textbbox((0, 0), text, font=fnt)
        h = bbox[3] - bbox[1]
        if h <= usable_h:
            best_size = mid
            lo = mid + 1
        else:
            hi = mid - 1

    return ImageFont.truetype(str(font_path), best_size)


def render_text_image(text: str, font_path: Path) -> Image.Image:
    """
    Render *text* with the given font at TARGET_HEIGHT pixels.
    Returns an RGB PIL image.
    """
    font = pick_font_size(font_path, text, TARGET_HEIGHT)

    # Measure exact bounding box
    img_tmp = Image.new("RGB", (1, 1))
    draw_tmp = ImageDraw.Draw(img_tmp)
    bbox = draw_tmp.textbbox((0, 0), text, font=font)
    text_w = max(bbox[2] - bbox[0], 1)
    text_h = max(bbox[3] - bbox[1], 1)

    img_w = text_w + 2 * MARGIN
    img = Image.new("RGB", (img_w, TARGET_HEIGHT), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Center vertically
    y_off = (TARGET_HEIGHT - text_h) // 2 - bbox[1]
    draw.text((MARGIN - bbox[0], y_off), text, font=font, fill=(0, 0, 0))

    return img


def apply_augmentations(img: Image.Image) -> Image.Image:
    """
    Apply random augmentations:
    * Gaussian blur  (radius 0–2)
    * Random skew    (−5° to +5°)
    * Background noise (Gaussian pixel noise, probability 0.5)
    """
    # 1. Random Gaussian blur
    blur_radius = random.uniform(*BLUR_RANGE)
    if blur_radius > 0.1:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

    # 2. Random skew (rotation with white fill, then crop/pad back to target height)
    angle = random.uniform(*SKEW_RANGE)
    if abs(angle) > 0.5:
        img = img.rotate(angle, expand=True, fillcolor=(255, 255, 255))
        w, h = img.size
        if h > TARGET_HEIGHT:
            # Crop symmetrically to remove the extra rows introduced by rotation.
            top = (h - TARGET_HEIGHT) // 2
            img = img.crop((0, top, w, top + TARGET_HEIGHT))
        elif h < TARGET_HEIGHT:
            # Pad with white to restore the target height.
            padded = Image.new("RGB", (w, TARGET_HEIGHT), color=(255, 255, 255))
            padded.paste(img, (0, (TARGET_HEIGHT - h) // 2))
            img = padded

    # 3. Background noise (Gaussian) — applied with 50 % probability
    if random.random() < 0.5:
        arr = np.array(img, dtype=np.float32)
        noise = np.random.normal(0, NOISE_STD, arr.shape)
        arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
        img = Image.fromarray(arr)

    return img


def generate_dataset(count: int) -> None:
    """Generate *count* labelled OCR images and write them to OUTPUT_DIR."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    words = load_words(INPUT_DICTS)
    fonts = load_fonts(INPUT_FONTS)

    if not words:
        raise ValueError("No words loaded from dictionary files.")

    labels_path = OUTPUT_DIR / "labels.txt"
    generated = 0

    with open(labels_path, "w", encoding="utf-8") as labels_file:
        with tqdm(total=count, desc="Generating", unit="img") as pbar:
            while generated < count:
                text, _is_cyr = random.choice(words)
                if not text:
                    continue

                font_path = random.choice(fonts)

                try:
                    img = render_text_image(text, font_path)
                    img = apply_augmentations(img)
                except (OSError, ValueError, TypeError, AttributeError) as exc:
                    # Skip problematic combinations silently
                    tqdm.write(f"[WARN] Skipping '{text[:30]}' with {font_path.name}: {exc}")
                    continue

                fname = f"{generated:06d}.jpg"
                img.convert("RGB").save(OUTPUT_DIR / fname, "JPEG", quality=95)
                labels_file.write(f"{fname}\t{text}\n")

                generated += 1
                pbar.update(1)

    print(f"\nDone! {generated} images saved to '{OUTPUT_DIR}'")
    print(f"Labels file: '{labels_path}'")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a synthetic Serbian OCR dataset (Cyrillic & Latin)."
    )
    parser.add_argument(
        "--count",
        "-n",
        type=int,
        default=1000,
        metavar="N",
        help="Total number of images to generate (default: 1000).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    generate_dataset(args.count)
