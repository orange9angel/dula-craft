---
name: dula-subtitles
description: Make and burn in polished dual-language subtitles for a finished video, with a color for each speaker and an optional opening card. Use for adding subtitles, captions, ASS subtitle files or hardcoded subtitles to a video or animation.
---

# Dual-language subtitles

```bash
python scripts/make_subs.py --events subs.json --ass-out subs.ass \
  --video film.mp4 --out-video film_subbed.mp4
```

For just the ASS file, leave out the last two arguments. The script path is relative to this SKILL.md, and it needs only ffmpeg.

Create `subs.json`. You write the translation yourself:

```json
{
  "group": "",
  "project": "",
  "events": [
    {"start": 0.3, "end": 2.8, "speaker": "Sam", "text": "Don't leave after school.", "translation": "Ne pars pas après l'école."}
  ]
}
```

- `text` is the main line, and `translation` is the smaller second line. Leave out `translation` for one language.
- Each `speaker` gets a color automatically, in order of appearance.
- Leave `group` and `project` empty for no opening card.
- Add `"fade": "300,500"` to an event to change its fade in and out, in milliseconds.
- Set the font with `--font`. The default depends on the system. If you see empty boxes, choose an installed font that covers the language.

## Watch out for

- Burn subtitles only onto a clean video. Burning onto a video that already has them gives you two sets.
- Leave wordless screams, songs and end credits without subtitles.
- Keep position, size and color the same across a series.
- When checking burned subtitles, put `-ss` after `-i`. Putting it first resets the subtitle timeline, so they look missing.
- Before handing over, look at a few frames to confirm subtitles appear and show no empty boxes.
