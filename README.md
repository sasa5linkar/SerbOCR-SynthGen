# SerbOCR-SynthGen
High-fidelity synthetic data generation for Serbian Cyrillic and Latin OCR, optimized for quantized Vision-Language Models.

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Add .ttf fonts (see input/fonts/README.md for recommendations)
cp /path/to/your/font.ttf input/fonts/

# 3. Validate that the fonts cover Serbian Latin + Cyrillic
python validate_fonts.py

# 4. Generate 1 000 labelled images
python generate.py --count 1000
```

Generated files land in `output/`:

```
output/
  000000.jpg
  000001.jpg
  ...
  labels.txt        # filename<TAB>ground_truth_text
```

## Directory structure

```
SerbOCR-SynthGen/
├── generate.py           # main generator script
├── requirements.txt
├── input/
│   ├── dicts/            # .txt word/sentence lists (UTF-8)
│   │   ├── serbian_cyrillic.txt
│   │   └── serbian_latin.txt
│   └── fonts/            # .ttf font files (not included — see README inside)
└── output/               # generated images + labels.txt (git-ignored)
```

## Features

| Feature | Detail |
|---------|--------|
| **Resolution** | 64 px height, variable width |
| **Augmentations** | Gaussian blur (radius 0–2), random skew (±5°), Gaussian pixel noise |
| **Dual-script** | Cyrillic-only dictionaries are auto-transliterated to Latin via *cyrtranslit* |
| **Encoding** | Full UTF-8 — preserves ђ, ћ, џ, š, č, ž, ć, đ, … |
| **Output format** | JPEG images + `labels.txt` with `filename<TAB>text` per line |

## CLI reference

```
usage: generate.py [-h] [--count N]

optional arguments:
  -h, --help       show this help message and exit
  --count N, -n N  Total number of images to generate (default: 1000)
```

```
usage: validate_fonts.py [-h] [--dicts-dir DICTS_DIR] [--fonts-dir FONTS_DIR]

Checks each font in `input/fonts/`, reports which fonts are missing required
Serbian Latin or Cyrillic characters used by the bundled dictionaries, and
exits with code `1` if any font fails.
```

## Adding more dictionaries

Drop any UTF-8 `.txt` file (one word or sentence per line) into `input/dicts/`.
The script automatically detects Cyrillic-only files and produces a matching
Latin-script transliteration, keeping both scripts balanced in the dataset.
