# Fonts directory

Place `.ttf` (TrueType) font files here before running `generate.py`.

## Recommended free fonts with Serbian Cyrillic & Latin support

| Font | Source |
|------|--------|
| Noto Sans / Noto Serif | <https://fonts.google.com/noto> |
| DejaVu Sans / DejaVu Serif | <https://dejavu-fonts.github.io> |
| FreeSerif / FreeSans / FreeMono | <https://www.gnu.org/software/freefont/> |
| Source Sans / Source Serif | <https://fonts.adobe.com/fonts/source-sans> |
| PT Sans / PT Serif | <https://fonts.google.com/specimen/PT+Sans> |

Download the `.ttf` files and copy them to this directory, then run:

```bash
python validate_fonts.py
python generate.py --count 5000
```

At least one font is required.  Using several fonts (5–20) is strongly
recommended so the generated images cover diverse visual styles.
