---
name: dula-title-card
description: Generate ink-style title cards entirely in code, with letters growing out of ink, a light sweep and floating bokeh. Use for opening titles, end cards, chapter cards, transitions, or covering a flaw between shots. Uses no image generation quota. Also for 字卡, 片头.
---

# Ink title cards

```bash
# Transition card: in from white, out to white
python scripts/make_title_card.py --bg background.png --title "Chapter One" --subtitle "Setting Out" \
  --title-size 120 --duration 1.2 --reveal 0.18,0.62 --out-mode white --out-dir build/card

# End card: fades to black
python scripts/make_title_card.py --bg background.png --title "The End" --title-size 120 \
  --duration 1.7 --reveal 0.15,0.85 --out-mode black --out-dir build/card

# Frames to video
ffmpeg -framerate 24 -i build/card/f_%03d.png -c:v libx264 -pix_fmt yuv420p -crf 18 card.mp4
```

The script path is relative to this SKILL.md. Output is always 1280×720, so use ffmpeg's `scale` when joining a film of another size. For environment problems, use `dula-start`.

| Option | Meaning |
|---|---|
| `--title-size`, `--title-y` | Text size (default 200) and vertical position (as a fraction of the frame) |
| `--seed` | A different number gives a different ink shape |
| `--fps` | Match the film. Default 24 |
| `--in-mode` | `white` fades in from white. Use `image` when the first frame must show a picture |
| `--font` | Font file. By default, a system font is chosen. A brush or calligraphic font carries the ink look best |

## Watch out for

- By default the first frame is pure white, so it can't be used as a cover. Use `--in-mode image` for that.
- Join the card into the film, then check its real opening, middle and exit frames. A screenshot of the clearest moment won't reveal problems.
- Always start joining from the clean video, not a version that already has cards.
