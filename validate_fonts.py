#!/usr/bin/env python3
"""
Validate that local font files cover the Serbian Latin and Cyrillic characters
required by this repository's dictionaries.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DICTS_DIR = BASE_DIR / "input" / "dicts"
DEFAULT_FONTS_DIR = BASE_DIR / "input" / "fonts"
WHITESPACE_CHARS = " \t\r\n\v\f"

SERBIAN_CORE_TEXT = (
    "АБВГДЂЕЖЗИЈКЛЉМНЊОПРСТЋУФХЦЧЏШ"
    "абвгдђежзијклљмнњопрстћуфхцчџш"
    "ČĆĐŠŽčćđšž"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check whether bundled fonts support Serbian Latin and Cyrillic characters."
    )
    parser.add_argument(
        "--dicts-dir",
        type=Path,
        default=DEFAULT_DICTS_DIR,
        help=f"Dictionary directory to scan (default: {DEFAULT_DICTS_DIR}).",
    )
    parser.add_argument(
        "--fonts-dir",
        type=Path,
        default=DEFAULT_FONTS_DIR,
        help=f"Font directory to scan (default: {DEFAULT_FONTS_DIR}).",
    )
    return parser.parse_args()


def ensure_fontconfig() -> None:
    if shutil.which("fc-query"):
        return
    raise RuntimeError(
        "Missing required system tool 'fc-query'. Install fontconfig to validate font "
        "coverage (for example: `apt install fontconfig`, `brew install fontconfig`, "
        "or `dnf install fontconfig`)."
    )


def load_required_characters(dicts_dir: Path) -> list[str]:
    txt_files = sorted(dicts_dir.glob("*.txt"))
    if not txt_files:
        raise FileNotFoundError(f"No .txt dictionary files found in {dicts_dir}")

    required_chars = set(SERBIAN_CORE_TEXT)
    for path in txt_files:
        text = path.read_text(encoding="utf-8")
        required_chars.update(set(text) - set(WHITESPACE_CHARS))

    return sorted(required_chars, key=ord)


def load_font_paths(fonts_dir: Path) -> list[Path]:
    fonts = sorted(fonts_dir.glob("*.ttf")) + sorted(fonts_dir.glob("*.otf"))
    if not fonts:
        raise FileNotFoundError(f"No .ttf or .otf font files found in {fonts_dir}")
    return fonts


def parse_charset_ranges(charset_output: str) -> set[int]:
    codepoints: set[int] = set()
    for token in charset_output.split():
        if "-" in token:
            start_hex, end_hex = token.split("-", 1)
            start = int(start_hex, 16)
            end = int(end_hex, 16)
            codepoints.update(range(start, end + 1))
        else:
            codepoints.add(int(token, 16))
    return codepoints


def read_font_charset(font_path: Path) -> set[int]:
    result = subprocess.run(
        ["fc-query", "--format=%{charset}\n", str(font_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return parse_charset_ranges(result.stdout.strip())


def format_missing_characters(chars: list[str]) -> str:
    formatted = []
    for char in chars:
        codepoint = f"{ord(char):X}"
        formatted.append(f"{char} (U+{codepoint.zfill(4)})")
    return ", ".join(formatted)


def main() -> int:
    args = parse_args()
    ensure_fontconfig()

    required_chars = load_required_characters(args.dicts_dir)
    font_paths = load_font_paths(args.fonts_dir)

    print(
        f"Validating {len(font_paths)} font(s) against {len(required_chars)} required Serbian characters..."
    )

    failing_fonts = 0
    for font_path in font_paths:
        supported = read_font_charset(font_path)
        missing = [char for char in required_chars if ord(char) not in supported]
        if missing:
            failing_fonts += 1
            print(f"FAIL {font_path.name}")
            print(f"  Missing: {format_missing_characters(missing)}")
        else:
            print(f"OK   {font_path.name}")

    if failing_fonts:
        print(f"\n{failing_fonts} font(s) are missing required Serbian character support.")
        return 1

    print("\nAll checked fonts support the required Serbian Latin and Cyrillic characters.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
